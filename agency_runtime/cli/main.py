"""Argparse command line interface for Agency Runtime.

Commands:
    agency install          — Install starter roster + profile
    agency configure        — Guided setup wizard (writes agency.yaml)
    agency doctor           — Health diagnostics
    agency config show      — Display effective config
    agency config set       — Set a config value
    agency config validate  — Validate config
    agency config path      — Print config file path
    agency roster list      — List active roster
    agency search <query>   — Search roster
    agency route <task>     — Route a task to agents
    agency delegate         — Delegate to a backend
    agency eval delegation  — Run deterministic delegation evals
    agency smoke --all      — Run deterministic local smoke checks
    agency db stats         — Show SQLite runtime table sizes
    agency db trim          — Trim append-only SQLite runtime tables
    agency sync             — Download/activate agents from sources
    agency source add       — Add a roster source
    agency serve            — Start HTTP server
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path
from typing import Any, Sequence

import yaml

from agency_runtime.core.config import (
    AgencyConfig,
    config_to_yaml,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.detect import (
    ProviderDetection,
    detect_all,
    generate_config_from_detection,
)
from agency_runtime.core.doctor import format_report_human, run_doctor
from agency_runtime.core.policy.defaults import STARTER_ROSTER
from agency_runtime.core.policy.profiles import PROFILES, get_profile
from agency_runtime.core.roster.sync import (
    activate_snapshot,
    approve_snapshot,
    create_roster_diff,
    download_from_source,
    quarantine_candidate,
    validate_agent,
)
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.store.sqlite import Store


def _store(config: AgencyConfig | None = None) -> Store:
    if config:
        return Store(config.store.resolved_path())
    return Store()


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


# ── Install ──────────────────────────────────────────────────


def _seed_starter_roster(store: Store) -> int:
    existing_slugs = {agent.get("agent_slug") for agent in store.get_active_roster()}
    count = 0
    for agent in STARTER_ROSTER:
        if agent["slug"] in existing_slugs:
            continue
        store.activate_agent(dict(agent))
        count += 1
    store.record_import_event("starter_roster_installed", "", f"count={count}")
    return count


def cmd_install(args: argparse.Namespace) -> int:
    """Install Agency Runtime — seeds roster AND wires into agent host(s).

    Usage:
        agency install                  — seed roster only (standalone)
        agency install --agent hermes   — wire into Hermes
        agency install --agent openclaw — wire into OpenClaw
        agency install --agent codex    — wire into Codex
        agency install --all            — auto-detect + wire into every agent found
    """
    from agency_runtime.core.installer import (
        detect_installed_agents,
        install_agent_adapter,
        seed_starter_roster,
    )

    cfg = load_config()
    profile = get_profile(args.profile)
    store = _store(cfg)

    # Always seed the roster
    count = seed_starter_roster(store)
    print(f"✅ Agency Runtime profile: {profile.name}")
    print(f"✅ Starter roster activated: {count} agents")
    print(f"   Config: {cfg.config_path or '(defaults only)'}")
    print(f"   Judge model: {cfg.judge.model} ({cfg.judge.base_url})")

    # Handle agent adapter installation
    if args.all:
        detected = detect_installed_agents()
        if not detected:
            print("\n⚠️  No supported AI agent hosts detected.")
            print("   Install Hermes, OpenClaw, Codex, or Claude Code first.")
            return 0
        print(f"\n🔍 Detected {len(detected)} agent host(s): {', '.join(detected)}")
        for agent in detected:
            result = install_agent_adapter(agent, cfg)
            if result["ok"]:
                print(f"✅ {agent}: wired → {result['plugin_path']}")
            else:
                print(f"❌ {agent}: {result['error']}")
    elif args.agent:
        result = install_agent_adapter(args.agent, cfg)
        if result["ok"]:
            print(f"\n✅ {args.agent}: wired → {result['plugin_path']}")
            print(f"   Restart {args.agent} to activate.")
        else:
            print(f"\n❌ {args.agent}: {result['error']}")
            return 1
    else:
        print(f"\n💡 To wire into an AI agent host, run:")
        print(f"   agency install --all          (auto-detect)")
        print(f"   agency install --agent hermes  (specific)")

    return 0


def cmd_on(args: argparse.Namespace) -> int:
    """Enable Agency Runtime for a specific agent host."""
    from agency_runtime.core.installer import toggle_agency, detect_installed_agents

    agent = args.agent
    if not agent:
        detected = detect_installed_agents()
        if len(detected) == 1:
            agent = detected[0]
        elif len(detected) == 0:
            print("No agent hosts detected. Use: agency on --agent hermes")
            return 1
        else:
            print(f"Multiple hosts detected: {', '.join(detected)}")
            print("Specify: agency on --agent <name>")
            return 1

    result = toggle_agency(agent, enabled=True)
    if result["ok"]:
        print(f"✅ Agency Runtime ENABLED for {agent}")
        print(f"   Restart {agent} to take effect.")
    else:
        print(f"❌ {result['error']}")
    return 0 if result["ok"] else 1


def cmd_off(args: argparse.Namespace) -> int:
    """Disable Agency Runtime for a specific agent host."""
    from agency_runtime.core.installer import toggle_agency, detect_installed_agents

    agent = args.agent
    if not agent:
        detected = detect_installed_agents()
        if len(detected) == 1:
            agent = detected[0]
        elif len(detected) == 0:
            print("No agent hosts detected. Use: agency off --agent hermes")
            return 1
        else:
            print(f"Multiple hosts detected: {', '.join(detected)}")
            print("Specify: agency off --agent <name>")
            return 1

    result = toggle_agency(agent, enabled=False)
    if result["ok"]:
        print(f"⏸️  Agency Runtime DISABLED for {agent}")
        print(f"   Plugin file moved to: {result.get('backup_path', 'disabled')}")
        print(f"   Restart {agent} to take effect.")
    else:
        print(f"❌ {result['error']}")
    return 0 if result["ok"] else 1


# ── Configure wizard ─────────────────────────────────────────


def cmd_configure(args: argparse.Namespace) -> int:
    """Guided setup wizard or non-interactive config generation."""
    import os

    config_path = Path(os.environ.get("AGENCY_CONFIG_PATH", str(Path.home() / ".agency-runtime" / "agency.yaml")))

    if config_path.exists() and not args.force:
        print(f"Config already exists at {config_path}")
        if not args.non_interactive:
            resp = input("Overwrite? [y/N] ").strip().lower()
            if resp != "y":
                print("Aborted.")
                return 0
        else:
            print("Use --force to overwrite in non-interactive mode.")
            return 1

    print("\nDetecting available providers...")
    detection = detect_all()
    p = detection.providers
    a = detection.adapters

    print(f"  {'✅' if p.ollama_available else '❌'} Ollama: {p.ollama_base_url}" +
          (f" ({len(p.ollama_models)} models)" if p.ollama_models else ""))
    print(f"  {'✅' if p.openai_key else '❌'} OpenAI API key: {'found' if p.openai_key else 'not set'}")
    print(f"  {'✅' if p.anthropic_key else '❌'} Anthropic API key: {'found' if p.anthropic_key else 'not set'}")
    print(f"  {'✅' if p.litellm_available else '❌'} LiteLLM proxy: {p.litellm_base_url}")
    print()
    print(f"  {'✅' if a.hermes else '❌'} Hermes adapter")
    print(f"  {'✅' if a.openclaw else '❌'} OpenClaw adapter")
    print(f"  {'✅' if a.codex else '❌'} Codex CLI")
    print(f"  {'✅' if a.claude else '❌'} Claude Code CLI")
    print()

    # Determine profile
    profile = args.profile or "standard"
    if args.profile == "local-only":
        pass  # user explicitly chose it
    elif not detection.has_any_provider and not args.non_interactive:
        print("No LLM providers detected. Recommend local-only profile.")
        resp = input("Use local-only profile? [Y/n] ").strip().lower()
        if resp != "n":
            profile = "local-only"

    if args.non_interactive:
        config_data = generate_config_from_detection(detection, profile=profile)
    else:
        config_data = _interactive_wizard(detection, profile)

    # Write config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Config written to {config_path}")

    # Install starter roster
    reset_config_cache()
    cfg = load_config(reload=True)
    store = _store(cfg)
    count = _seed_starter_roster(store)
    print(f"✅ Starter roster installed: {count} agents")
    print(f"✅ SQLite database initialized: {cfg.store.resolved_path()}")
    print(f"\nNext steps:")
    print(f"  agency doctor              — verify everything is working")
    print(f"  agency search \"code review\" — test the selector")
    print(f"  agency route \"review this PR\" — see routing in action")
    return 0


def _interactive_wizard(detection, profile: str) -> dict[str, Any]:
    """Interactive wizard — prompts for each decision with full model discovery."""
    p = detection.providers

    print("Step 1: Judge Model")
    print("━" * 40)

    # ── Build provider menu ────────────────────────────────────
    # Each entry: (menu_label, handler_fn)
    # The handler returns a judge_cfg dict
    providers: list[tuple[str, str]] = []

    if p.ollama_available:
        n = len(p.ollama_models)
        providers.append(("ollama", f"Ollama (free, local) — {n} model(s) available"))

    if p.openai_key_present:
        n = len(p.openai_models)
        suffix = f" — {n} model(s) discovered" if n else " (model list unavailable)"
        providers.append(("openai", f"OpenAI API (key detected){suffix}"))

    if p.anthropic_key_present:
        providers.append(("anthropic", "Anthropic API (key detected)"))

    if p.litellm_available:
        n = len(p.litellm_models)
        suffix = f" — {n} model group(s) discovered" if n else " (model list unavailable)"
        providers.append(("litellm", f"LiteLLM proxy{suffix}"))

    providers.append(("custom", "Custom OpenAI-compatible endpoint (OpenRouter, Together, Groq, LM Studio, etc.)"))

    print("\nWhich provider should the Agency selector use for routing?\n")
    for i, (_, label) in enumerate(providers, 1):
        print(f"  [{i}] {label}")

    choice_idx = _prompt_choice(len(providers), default=1) - 1
    provider_key = providers[choice_idx][0]

    # ── Per-provider model selection ──────────────────────────

    if provider_key == "ollama":
        judge_cfg = _pick_ollama_model(p)
    elif provider_key == "openai":
        judge_cfg = _pick_openai_model(p)
    elif provider_key == "anthropic":
        judge_cfg = _pick_anthropic_model()
    elif provider_key == "litellm":
        judge_cfg = _pick_litellm_model(p)
    else:
        judge_cfg = _pick_custom_endpoint()

    # Step 2: Profile
    print("\nStep 2: Install Profile")
    print("━" * 40)
    print("  [1] local-only — No network, no auto-sync, bundled roster only (safest)")
    print("  [2] standard   — Network enabled, no auto-sync (recommended)")
    print("  [3] power      — Network enabled, manual sync")
    print("  [4] yolo       — Network enabled, trusted-source nightly auto-sync")
    profile_choice = _prompt_choice(4, default=2)
    profile = ["local-only", "standard", "power", "yolo"][profile_choice - 1]

    # Step 3: Adapters
    print("\nStep 3: Host Adapters")
    print("━" * 40)
    a = detection.adapters
    adapters_cfg: dict[str, Any] = {}

    # LiteLLM adapter config
    litellm_detected = p.litellm_available
    icon = "✅" if litellm_detected else "❌"
    print(f"  {icon} LiteLLM proxy: {'detected' if litellm_detected else 'not detected'}")
    litellm_skip = ["complexity_router", "auto_router/"]
    # If we chose LiteLLM as judge, add the model to skip_models to prevent recursion
    if judge_cfg.get("base_url") == p.litellm_base_url and judge_cfg.get("model"):
        if judge_cfg["model"] not in litellm_skip:
            litellm_skip.append(judge_cfg["model"])
    adapters_cfg["litellm"] = {
        "enabled": "true" if litellm_detected else ("false" if profile == "local-only" else "auto"),
        "base_url": p.litellm_base_url,
        "api_key_env": "LITELLM_API_KEY",
        "skip_models": litellm_skip,
    }

    for name, detected in [
        ("hermes", a.hermes),
        ("openclaw", a.openclaw),
        ("codex", a.codex),
        ("claude", a.claude),
    ]:
        icon = "✅" if detected else "❌"
        print(f"  {icon} {name}: {'detected' if detected else 'not detected'}")
        adapters_cfg[name] = {
            "enabled": "true" if detected and profile != "local-only" else "auto"
        }

    # Step 4: Tuning
    print("\nStep 4: Advanced Tuning")
    print("━" * 40)
    print("Use default tuning values? (confidence=0.4, timeout=15s, max_selected=3)")
    resp = input("  [Y/n] ").strip().lower()
    if resp == "n":
        timeout = float(input("  Judge timeout (seconds): ") or "15")
        max_sel = int(input("  Max selected agents: ") or "3")
        threshold = float(input("  Confidence bypass threshold: ") or "15")
    else:
        timeout, max_sel, threshold = 15.0, 3, 15.0

    judge_cfg["timeout"] = timeout
    judge_cfg["max_selected"] = max_sel
    judge_cfg["confidence_bypass_threshold"] = threshold

    # Step 5: Review
    print("\nStep 5: Review")
    print("━" * 40)

    config_data = {
        "judge": judge_cfg,
        "ollama": {
            "enabled": p.ollama_available,
            "base_url": p.ollama_base_url,
        },
        "selector": {"min_confidence": 0.4, "max_user_msg_len": 4000, "trivial_msg_threshold": 12},
        "store": {"db_path": "~/.agency-runtime/agency.db"},
        "server": {"host": "127.0.0.1", "port": 7800},
        "adapters": adapters_cfg,
        "profile": profile,
        "companion_policy_path": None,
    }

    # Show summary
    _print_config_summary(config_data)

    return config_data


def _pick_ollama_model(p: ProviderDetection) -> dict[str, Any]:
    """Let user pick from discovered Ollama models or enter a custom one."""
    if not p.ollama_models:
        print("\nNo Ollama models discovered. Enter manually.")
        model = input("Model name (e.g. qwen3.5:2b): ").strip()
        if not model:
            model = "qwen3.5:2b"
        return {
            "model": model,
            "base_url": p.ollama_base_url,
            "api_key": "",
            "ollama_mode": True,
        }

    print(f"\nOllama models available ({len(p.ollama_models)}):")
    for i, model in enumerate(p.ollama_models[:15], 1):
        print(f"  [{i}] {model}")
    if len(p.ollama_models) > 15:
        print(f"  ... and {len(p.ollama_models) - 15} more")
    print(f"  [{min(len(p.ollama_models) + 1, 16)}] Enter custom model name")

    choice = _prompt_choice(min(len(p.ollama_models) + 1, 16), default=1)
    if choice <= len(p.ollama_models):
        model = p.ollama_models[choice - 1]
    else:
        model = input("Model name: ").strip() or "qwen3.5:2b"

    return {
        "model": model,
        "base_url": p.ollama_base_url,
        "api_key": "",
        "ollama_mode": True,
    }


def _pick_openai_model(p: ProviderDetection) -> dict[str, Any]:
    """Let user pick from discovered OpenAI models or enter a custom one."""
    from agency_runtime.core.detect import _OPENAI_SUGGESTIONS

    base_url = "https://api.openai.com/v1"

    # Merge discovered + suggestions, dedup, preserve order
    all_models: list[str] = []
    seen = set()
    for m in p.openai_models + _OPENAI_SUGGESTIONS:
        if m not in seen:
            all_models.append(m)
            seen.add(m)

    print(f"\nOpenAI models available:")
    for i, model in enumerate(all_models[:15], 1):
        discovered = "✅" if model in p.openai_models else "  "
        print(f"  [{i}] {discovered} {model}")
    if len(all_models) > 15:
        print(f"  ... and {len(all_models) - 15} more")
    print(f"  [{min(len(all_models) + 1, 16)}] Enter custom model name")

    choice = _prompt_choice(min(len(all_models) + 1, 16), default=1)
    if choice <= len(all_models):
        model = all_models[choice - 1]
    else:
        model = input("Model name (e.g. gpt-4o-mini): ").strip()
        if not model:
            model = "gpt-4o-mini"

    return {
        "model": model,
        "base_url": base_url,
        "api_key_env": "OPENAI_API_KEY",
        "ollama_mode": False,
    }


def _pick_anthropic_model() -> dict[str, Any]:
    """Let user pick an Anthropic model."""
    from agency_runtime.core.detect import _ANTHROPIC_SUGGESTIONS

    print(f"\nAnthropic models:")
    for i, model in enumerate(_ANTHROPIC_SUGGESTIONS, 1):
        print(f"  [{i}] {model}")
    print(f"  [{len(_ANTHROPIC_SUGGESTIONS) + 1}] Enter custom model name")

    choice = _prompt_choice(len(_ANTHROPIC_SUGGESTIONS) + 1, default=1)
    if choice <= len(_ANTHROPIC_SUGGESTIONS):
        model = _ANTHROPIC_SUGGESTIONS[choice - 1]
    else:
        model = input("Model name: ").strip()
        if not model:
            model = "claude-3-5-sonnet-20241022"

    return {
        "model": model,
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
        "ollama_mode": False,
    }


def _pick_litellm_model(p: ProviderDetection) -> dict[str, Any]:
    """Let user pick from discovered LiteLLM model groups or enter one."""
    if p.litellm_models:
        print(f"\nLiteLLM model groups available ({len(p.litellm_models)}):")
        for i, model in enumerate(p.litellm_models[:15], 1):
            print(f"  [{i}] {model}")
        if len(p.litellm_models) > 15:
            print(f"  ... and {len(p.litellm_models) - 15} more")
        print(f"  [{min(len(p.litellm_models) + 1, 16)}] Enter custom model group name")

        choice = _prompt_choice(min(len(p.litellm_models) + 1, 16), default=1)
        if choice <= len(p.litellm_models):
            model = p.litellm_models[choice - 1]
        else:
            model = input("Model group name: ").strip()
    else:
        print("\nCouldn't discover LiteLLM models (proxy may need an API key).")
        print("Enter your LiteLLM model group name.")
        print("Common patterns: task-general, gpt-4o-mini, claude-sonnet, etc.")
        model = input("Model group name: ").strip()
        if not model:
            model = "task-general"

    # Verify API key situation
    key_env = "LITELLM_API_KEY"
    litellm_key = os.environ.get("LITELLM_API_KEY", "")
    if not litellm_key:
        print("\n⚠️  LITELLM_API_KEY not set in environment.")
        print("LiteLLM proxy may require a key. You can:")
        print("  [1] Use a different env var name")
        print("  [2] Enter the key directly (stored in config)")
        print("  [3] Skip — my LiteLLM doesn't need a key")
        key_choice = _prompt_choice(3, default=3)
        if key_choice == 1:
            key_env = input("Env var name: ").strip() or "LITELLM_API_KEY"
        elif key_choice == 2:
            direct_key = input("API key: ").strip()
            return {
                "model": model,
                "base_url": p.litellm_base_url,
                "api_key": direct_key,
                "ollama_mode": False,
            }

    return {
        "model": model,
        "base_url": p.litellm_base_url,
        "api_key_env": key_env,
        "ollama_mode": False,
    }


def _pick_custom_endpoint() -> dict[str, Any]:
    """Let user configure any OpenAI-compatible endpoint."""
    print("\nCustom OpenAI-compatible endpoint")
    print("Works with: OpenRouter, Together AI, Groq, LM Studio, Ollama")
    print("             (via OpenAI compat), Azure OpenAI, etc.\n")

    # Common presets
    presets = [
        ("OpenRouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY"),
        ("Together AI", "https://api.together.xyz/v1", "TOGETHER_API_KEY"),
        ("Groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY"),
        ("LM Studio (local)", "http://127.0.0.1:1234/v1", ""),
        ("Enter manually", "", ""),
    ]

    print("Choose a provider preset or enter manually:\n")
    for i, (name, _, _) in enumerate(presets, 1):
        print(f"  [{i}] {name}")

    choice = _prompt_choice(len(presets), default=len(presets))

    if choice <= len(presets) - 1:
        _, base_url, default_key_env = presets[choice - 1]
        base_url = base_url or input("Base URL: ").strip()
    else:
        base_url = input("Base URL (e.g. https://api.example.com/v1): ").strip()

    # Try to discover models at this endpoint
    print(f"\nDiscovering models at {base_url}...")
    key_env = default_key_env or ""
    api_key = os.environ.get(key_env, "") if key_env else ""
    models = _fetch_models_custom(base_url, api_key)

    if models:
        print(f"Found {len(models)} models:")
        for i, model in enumerate(models[:15], 1):
            print(f"  [{i}] {model}")
        if len(models) > 15:
            print(f"  ... and {len(models) - 15} more")
        print(f"  [{min(len(models) + 1, 16)}] Enter custom model name")

        model_choice = _prompt_choice(min(len(models) + 1, 16), default=1)
        if model_choice <= len(models):
            model = models[model_choice - 1]
        else:
            model = input("Model name: ").strip()
    else:
        print("Could not discover models (endpoint may need an API key).")
        model = input("Enter model name: ").strip()

    # API key
    if key_env and api_key:
        print(f"\nUsing API key from ${key_env}")
    elif key_env:
        print(f"\n⚠️  ${key_env} not set in environment.")
        key_choice = input(f"Press Enter to use ${key_env} env var, or type key directly: ").strip()
        if key_choice:
            return {
                "model": model,
                "base_url": base_url,
                "api_key": key_choice,
                "ollama_mode": False,
            }
    else:
        key_input = input("API key env var name (blank for no key): ").strip()
        if key_input:
            key_env = key_input

    result: dict[str, Any] = {
        "model": model,
        "base_url": base_url,
        "ollama_mode": False,
    }
    if key_env:
        result["api_key_env"] = key_env
    else:
        result["api_key"] = ""

    return result


def _fetch_models_custom(base_url: str, api_key: str | None = None) -> list[str]:
    """Fetch models from a custom OpenAI-compatible endpoint."""
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/models",
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            import json
            data = json.loads(resp.read().decode("utf-8"))
        return sorted([
            m.get("id", m.get("model", ""))
            for m in data.get("data", [])
            if m.get("id") or m.get("model")
        ])
    except Exception:
        return []


def _print_config_summary(config_data: dict[str, Any]) -> None:
    """Print a human-readable summary of the generated config."""
    j = config_data.get("judge", {})
    print(f"\n  Judge model:  {j.get('model', '?')}")
    print(f"  Base URL:     {j.get('base_url', '?')}")
    if j.get("api_key_env"):
        print(f"  API key:      from ${j['api_key_env']}")
    elif j.get("api_key"):
        print(f"  API key:      (stored in config)")
    else:
        print(f"  API key:      none (free/local)")
    print(f"  Ollama mode:  {j.get('ollama_mode', False)}")
    print(f"  Profile:      {config_data.get('profile', 'standard')}")


def _prompt_choice(max_val: int, default: int = 1) -> int:
    while True:
        raw = input(f"> ").strip()
        if not raw:
            return default
        try:
            val = int(raw)
            if 1 <= val <= max_val:
                return val
        except ValueError:
            pass
        print(f"  Enter a number 1-{max_val}")


# ── Doctor ───────────────────────────────────────────────────


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config()
    report = run_doctor(cfg)
    if args.json:
        _print_json(report.to_dict())
    else:
        print(format_report_human(report))
    return report.exit_code


# ── Config subcommands ───────────────────────────────────────


def cmd_config_show(args: argparse.Namespace) -> int:
    cfg = load_config()
    print(config_to_yaml(cfg, redact=not args.raw))
    return 0


def cmd_config_path(args: argparse.Namespace) -> int:
    cfg = load_config()
    print(cfg.config_path or "(no config file — using bundled defaults)")
    return 0


def cmd_config_get(args: argparse.Namespace) -> int:
    cfg = load_config()
    # Navigate dotted path: judge.model, ollama.enabled, etc.
    parts = args.key.split(".")
    val: Any = cfg
    for part in parts:
        if hasattr(val, part):
            val = getattr(val, part)
        elif hasattr(val, "__getitem__"):
            try:
                val = val[part]
            except (KeyError, TypeError):
                print(f"Key not found: {args.key}", file=sys.stderr)
                return 1
        else:
            print(f"Key not found: {args.key}", file=sys.stderr)
            return 1
    print(json.dumps(val) if isinstance(val, (list, tuple)) else val)
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    cfg = load_config()
    config_path = Path(cfg.config_path) if cfg.config_path else Path.home() / ".agency-runtime" / "agency.yaml"

    # Load existing YAML or defaults
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
    else:
        data = {}

    # Navigate dotted path and set value
    parts = args.key.split(".")
    target = data
    for part in parts[:-1]:
        if part not in target or not isinstance(target[part], dict):
            target[part] = {}
        target = target[part]

    # Try to parse as number/bool/yaml
    try:
        value = yaml.safe_load(args.value)
    except yaml.YAMLError:
        value = args.value

    target[parts[-1]] = value

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    print(f"Set {args.key} = {value}")
    return 0


def cmd_config_validate(args: argparse.Namespace) -> int:
    """Validate config by running doctor checks."""
    cfg = load_config()
    report = run_doctor(cfg)
    if report.exit_code == 0:
        print("✅ Config valid — all checks passed")
    elif report.exit_code == 2:
        print("⚠️  Config valid — degraded (some features unavailable)")
    else:
        print("❌ Config has issues — see doctor output")
    # Print only the failed/warned checks
    for check in report.checks:
        if check.status in ("warn", "fail"):
            icon = "⚠️ " if check.status == "warn" else "❌"
            print(f"  {icon} {check.name}: {check.message}")
    return report.exit_code


def cmd_config_reset(args: argparse.Namespace) -> int:
    """Reset config to defaults."""
    cfg = load_config()
    config_path = Path(cfg.config_path) if cfg.config_path else Path.home() / ".agency-runtime" / "agency.yaml"
    if config_path.exists():
        resp = input(f"Delete {config_path} and reset to defaults? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return 0
        config_path.unlink()
    print(f"Config reset. Run `agency configure` to set up again.")
    return 0


# ── Sync ─────────────────────────────────────────────────────


def cmd_sync(args: argparse.Namespace) -> int:
    store = _store()
    sources = store.list_agent_sources()
    if not sources:
        print("No enabled sources configured. Add one with: agency source add <url>", file=sys.stderr)
        return 1
    if args.auto_approve:
        untrusted = [source for source in sources if not int(source.get("trusted_for_auto_approve") or 0)]
        if untrusted:
            names = ", ".join(str(source.get("name") or source.get("url")) for source in untrusted)
            print(
                "Refusing --auto-approve because these sources are not trusted: " + names,
                file=sys.stderr,
            )
            print("Mark an intended source with: agency source add <url> --trusted-for-auto-approve", file=sys.stderr)
            return 1
    quarantined: list[str] = []
    errors: list[dict[str, str]] = []
    for source in sources:
        try:
            candidates = download_from_source(source["url"])
        except Exception as exc:
            errors.append({"source": source["url"], "error": str(exc)})
            continue
        if not candidates:
            errors.append({"source": source["url"], "error": "source returned zero candidates"})
            continue
        for agent in candidates:
            ok, reason = validate_agent(agent)
            if not ok:
                errors.append({"source": source["url"], "agent": agent.get("slug", ""), "error": reason})
                continue
            if args.dry_run:
                quarantined.append(agent["slug"])
            else:
                candidate_id = quarantine_candidate(agent, source["id"], store)
                quarantined.append(candidate_id)
    if args.dry_run:
        _print_json({"dry_run": True, "valid_candidates": quarantined, "errors": errors})
        return 0 if not errors else 2
    if args.auto_approve and errors:
        _print_json({"errors": errors})
        return 2
    if args.auto_approve and not quarantined:
        print("Refusing --auto-approve because no candidates were quarantined", file=sys.stderr)
        return 1
    diff = create_roster_diff(store, candidate_ids=quarantined)
    if args.review:
        _print_json(diff["diff"])
    if args.auto_approve:
        approve_snapshot(store, diff["snapshot_id"])
        activate_snapshot(store, diff["snapshot_id"])
        _print_json({
            "snapshot_id": diff["snapshot_id"],
            "activated": True,
            "candidate_count": len(quarantined),
            "diff": diff["diff"],
        })
    else:
        print(f"Created snapshot {diff['snapshot_id']} from {len(quarantined)} candidates")
        print("Approve with: agency roster approve " + diff["snapshot_id"])
    if errors:
        _print_json({"errors": errors})
        return 2
    return 0


def cmd_source_add(args: argparse.Namespace) -> int:
    source_id = _store().add_agent_source(
        args.url,
        args.name or args.url,
        trusted_for_auto_approve=args.trusted_for_auto_approve,
    )
    print(source_id)
    return 0


def cmd_source_list(args: argparse.Namespace) -> int:
    del args
    _print_json(_store().list_agent_sources())
    return 0


def cmd_roster_list(args: argparse.Namespace) -> int:
    del args
    roster = _store().get_active_roster_as_catalog()
    for agent in roster:
        print(f"{agent['slug']}\t{agent.get('name', '')}\t{agent.get('division', '')}\t{agent.get('description', '')}")
    return 0


def cmd_roster_diff(args: argparse.Namespace) -> int:
    diff = create_roster_diff(_store())
    _print_json(diff if args.json else diff["diff"])
    return 0


def cmd_roster_approve(args: argparse.Namespace) -> int:
    approve_snapshot(_store(), args.snapshot_id)
    print(f"Approved snapshot {args.snapshot_id}")
    return 0


def cmd_roster_activate(args: argparse.Namespace) -> int:
    activate_snapshot(_store(), args.snapshot_id)
    print(f"Activated snapshot {args.snapshot_id}")
    return 0


def _search(query: str, limit: int) -> list[dict[str, Any]]:
    catalog = _store().get_active_roster_as_catalog()
    candidates, scores = pre_narrow(query, catalog, limit=limit)
    return [{**agent, "score": score} for agent, score in zip(candidates, scores)]


def cmd_search(args: argparse.Namespace) -> int:
    results = _search(args.query, args.limit)
    if args.json:
        _print_json(results)
    else:
        for agent in results:
            print(f"{agent['score']:.1f}\t{agent['slug']}\t{agent.get('name', '')}\t{agent.get('description', '')}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    results = _search(args.task, args.limit)
    if not results:
        print("No active agents available", file=sys.stderr)
        return 1
    top = results[0]
    if args.json:
        _print_json({"task": args.task, "selected": top, "candidates": results})
    else:
        print(f"selected: {top['slug']} ({top.get('name', '')}) score={top['score']:.1f}")
        for agent in results[1:]:
            print(f"candidate: {agent['slug']} score={agent['score']:.1f}")
    return 0


def _run_command(command: list[str]) -> int:
    if not command:
        print("No command supplied", file=sys.stderr)
        return 2
    import subprocess
    proc = subprocess.run(command, text=True)  # noqa: S603
    return int(proc.returncode)


def cmd_delegate(args: argparse.Namespace) -> int:
    backend = args.backend
    task = args.task
    agent = args.agent
    store = _store()
    trace_id = f"cli-delegate-{agent or 'auto'}"
    event_id = store.record_delegation(trace_id=trace_id, recommended_agent=agent or "", status="started", backend=backend)
    if backend == "codex":
        command = ["codex", "exec", task]
    elif backend == "claude":
        command = ["claude", "-p", "--output-format", "json", task]
    elif backend == "hermes":
        command = ["hermes", "-z", task]
    else:
        print(f"Delegation recorded for backend={backend} agent={agent}: {task}")
        store.update_delegation(event_id, status="suggested", backend=backend)
        return 0
    executable = shutil.which(command[0])
    if not executable:
        error = f"backend executable not found: {command[0]}"
        store.update_delegation(event_id, status="skipped", backend=backend, error=error, skip_reason=error)
        print(error, file=sys.stderr)
        return 127
    command[0] = executable
    code = _run_command(command)
    store.update_delegation(event_id, status="completed" if code == 0 else "failed", backend=backend, error="" if code == 0 else f"exit={code}")
    return code


def cmd_eval_delegation(args: argparse.Namespace) -> int:
    from agency_runtime.core.evals.delegation import run_delegation_eval

    report = run_delegation_eval()
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(f"delegation eval {status}: {report['passed_count']} passed, {report['failed_count']} failed")
        for case in report["cases"]:
            marker = "ok" if case["passed"] else "FAIL"
            detail = case.get("error") or case.get("detail") or ""
            print(f"{marker}\t{case['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_smoke(args: argparse.Namespace) -> int:
    from agency_runtime.core.smoke import run_smoke

    report = run_smoke(all_hosts=args.all)
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(f"smoke {status}: {report['passed_count']} passed, {report['failed_count']} failed, {report['skipped_count']} skipped")
        for check in report["checks"]:
            marker = {"pass": "ok", "skip": "skip", "fail": "FAIL"}.get(check["status"], check["status"])
            detail = check.get("error") or check.get("detail") or ""
            print(f"{marker}\t{check['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_db_stats(args: argparse.Namespace) -> int:
    stats = _store().database_stats()
    if args.json:
        _print_json(stats)
    else:
        print(f"DB: {stats['db_path']}")
        print(f"Size: {stats['db_size_bytes']} bytes (wal={stats['wal_size_bytes']}, shm={stats['shm_size_bytes']})")
        for table, count in stats["tables"].items():
            print(f"{table}\t{count}")
    return 0


def cmd_db_trim(args: argparse.Namespace) -> int:
    report = _store().trim_runtime_tables(
        older_than_days=args.older_than_days,
        keep_last=args.keep_last,
        dry_run=args.dry_run,
        vacuum=not args.no_vacuum,
    )
    if args.json:
        _print_json(report)
    else:
        mode = "DRY RUN " if report["dry_run"] else ""
        print(f"{mode}Trimmed Agency Runtime DB: {report['db_path']}")
        print(f"Size: {report['db_size_before_bytes']} -> {report['db_size_after_bytes']} bytes")
        for table, detail in report["tables"].items():
            deleted = int(detail.get("deleted", 0))
            if deleted:
                print(f"{table}\tdeleted={deleted}")
        if not any(int(detail.get("deleted", 0)) for detail in report["tables"].values()):
            print("No rows matched the retention policy.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from agency_runtime.server.http import serve
    serve()
    return 0


def cmd_codex_exec(args: argparse.Namespace) -> int:
    return _run_command(["codex", "exec", *args.args])


def cmd_run(args: argparse.Namespace) -> int:
    return _run_command(args.args)


# ── Parser ───────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agency", description="Agency Runtime Control Plane")
    sub = parser.add_subparsers(dest="command", required=True)

    # install
    install = sub.add_parser("install", help="Install Agency Runtime — seed roster + wire into agent hosts")
    install.add_argument("--profile", choices=sorted(PROFILES), default="standard")
    install.add_argument("--all", action="store_true", help="Auto-detect and wire into every AI agent host found")
    install.add_argument("--agent", choices=["hermes", "openclaw", "codex", "claude"], default=None,
                         help="Wire into a specific agent host")
    install.set_defaults(func=cmd_install)

    # on/off toggle
    on_p = sub.add_parser("on", help="Enable Agency Runtime for a host")
    on_p.add_argument("--agent", choices=["hermes", "openclaw", "codex", "claude"], default=None)
    on_p.set_defaults(func=cmd_on)

    off_p = sub.add_parser("off", help="Disable Agency Runtime for a host")
    off_p.add_argument("--agent", choices=["hermes", "openclaw", "codex", "claude"], default=None)
    off_p.set_defaults(func=cmd_off)

    # configure
    configure = sub.add_parser("configure", help="Guided setup wizard — writes agency.yaml")
    configure.add_argument("--non-interactive", action="store_true", help="Write detected config without prompts")
    configure.add_argument("--profile", choices=sorted(PROFILES), default=None)
    configure.add_argument("--force", action="store_true", help="Overwrite existing config")
    configure.set_defaults(func=cmd_configure)

    # doctor
    doctor = sub.add_parser("doctor", help="Check DB, config, providers, and adapter availability")
    doctor.add_argument("--json", action="store_true", help="JSON output")
    doctor.add_argument("--verbose", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    # config
    config = sub.add_parser("config", help="Non-interactive config helpers")
    config_sub = config.add_subparsers(dest="config_command", required=True)

    config_show = config_sub.add_parser("show", help="Print effective config")
    config_show.add_argument("--raw", action="store_true", help="Show secrets")
    config_show.set_defaults(func=cmd_config_show)

    config_path = config_sub.add_parser("path", help="Print config file location")
    config_path.set_defaults(func=cmd_config_path)

    config_get = config_sub.add_parser("get", help="Get a config value")
    config_get.add_argument("key", help="Dotted key (e.g. judge.model)")
    config_get.set_defaults(func=cmd_config_get)

    config_set = config_sub.add_parser("set", help="Set a config value")
    config_set.add_argument("key", help="Dotted key (e.g. judge.model)")
    config_set.add_argument("value", help="Value to set")
    config_set.set_defaults(func=cmd_config_set)

    config_validate = config_sub.add_parser("validate", help="Validate config + reachability")
    config_validate.set_defaults(func=cmd_config_validate)

    config_reset = config_sub.add_parser("reset", help="Reset to defaults")
    config_reset.set_defaults(func=cmd_config_reset)

    # sync
    sync = sub.add_parser("sync", help="Download sources into quarantine and create a roster snapshot")
    sync.add_argument("--dry-run", action="store_true")
    sync.add_argument("--review", action="store_true")
    sync.add_argument("--auto-approve", action="store_true")
    sync.set_defaults(func=cmd_sync)

    # source
    source = sub.add_parser("source", help="Manage roster sources")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_add = source_sub.add_parser("add", help="Add a roster source")
    source_add.add_argument("url")
    source_add.add_argument("--name", default="")
    source_add.add_argument(
        "--trusted-for-auto-approve",
        action="store_true",
        help="Allow this source to be used with sync --auto-approve automation",
    )
    source_add.set_defaults(func=cmd_source_add)
    source_list = source_sub.add_parser("list", help="List roster sources")
    source_list.set_defaults(func=cmd_source_list)

    # roster
    roster = sub.add_parser("roster", help="Inspect and activate roster snapshots")
    roster_sub = roster.add_subparsers(dest="roster_command", required=True)
    roster_list = roster_sub.add_parser("list", help="List active roster")
    roster_list.set_defaults(func=cmd_roster_list)
    roster_diff = roster_sub.add_parser("diff", help="Create/show diff for quarantined candidates")
    roster_diff.add_argument("--json", action="store_true")
    roster_diff.set_defaults(func=cmd_roster_diff)
    roster_approve = roster_sub.add_parser("approve", help="Approve snapshot")
    roster_approve.add_argument("snapshot_id")
    roster_approve.set_defaults(func=cmd_roster_approve)
    roster_activate = roster_sub.add_parser("activate", help="Activate approved snapshot")
    roster_activate.add_argument("snapshot_id")
    roster_activate.set_defaults(func=cmd_roster_activate)

    # search
    search = sub.add_parser("search", help="Search active roster")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--json", action="store_true")
    search.set_defaults(func=cmd_search)

    # route
    route = sub.add_parser("route", help="Route a task to candidate agents")
    route.add_argument("task")
    route.add_argument("--limit", type=int, default=5)
    route.add_argument("--json", action="store_true")
    route.set_defaults(func=cmd_route)

    # delegate
    delegate = sub.add_parser("delegate", help="Delegate a task to a backend")
    delegate.add_argument("--backend", default="generic")
    delegate.add_argument("--agent", default="")
    delegate.add_argument("--task", required=True)
    delegate.set_defaults(func=cmd_delegate)

    # eval
    eval_p = sub.add_parser("eval", help="Run deterministic eval suites")
    eval_sub = eval_p.add_subparsers(dest="eval_command", required=True)
    eval_delegation = eval_sub.add_parser("delegation", help="Run delegation lifecycle/evidence evals")
    eval_delegation.add_argument("--json", action="store_true")
    eval_delegation.set_defaults(func=cmd_eval_delegation)

    # smoke
    smoke = sub.add_parser("smoke", help="Run deterministic local smoke checks")
    smoke.add_argument("--all", action="store_true", help="Smoke-test every supported generated host plugin")
    smoke.add_argument("--json", action="store_true")
    smoke.set_defaults(func=cmd_smoke)

    # db
    db_p = sub.add_parser("db", help="Inspect and trim the SQLite store")
    db_sub = db_p.add_subparsers(dest="db_command", required=True)
    db_stats = db_sub.add_parser("stats", help="Show row counts and file sizes")
    db_stats.add_argument("--json", action="store_true")
    db_stats.set_defaults(func=cmd_db_stats)
    db_trim = db_sub.add_parser("trim", help="Trim append-only runtime/audit tables")
    db_trim.add_argument("--older-than-days", type=int, default=None, help="Delete runtime rows older than N days")
    db_trim.add_argument("--keep-last", type=int, default=None, help="Keep only the newest N rows per runtime table")
    db_trim.add_argument("--dry-run", action="store_true", help="Report rows that would be deleted without changing the DB")
    db_trim.add_argument("--no-vacuum", action="store_true", help="Skip VACUUM after deleting rows")
    db_trim.add_argument("--json", action="store_true")
    db_trim.set_defaults(func=cmd_db_trim)

    # serve
    serve_p = sub.add_parser("serve", help="Start HTTP server")
    serve_p.set_defaults(func=cmd_serve)

    # codex
    codex = sub.add_parser("codex", help="Codex adapter commands")
    codex_sub = codex.add_subparsers(dest="codex_command", required=True)
    codex_exec = codex_sub.add_parser("exec", help="Run codex exec")
    codex_exec.add_argument("args", nargs=argparse.REMAINDER)
    codex_exec.set_defaults(func=cmd_codex_exec)

    # run
    run = sub.add_parser("run", help="Run an arbitrary command")
    run.add_argument("args", nargs=argparse.REMAINDER)
    run.set_defaults(func=cmd_run)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"agency: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
