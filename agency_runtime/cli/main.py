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
    agency eval routing     — Run quantitative routing/policy/delegation gates
    agency eval delegation  — Run deterministic delegation lifecycle evals
    agency smoke --all      — Run deterministic local smoke checks
    agency db stats         — Show SQLite runtime table sizes
    agency db trim          — Trim append-only SQLite runtime tables
    agency sync             — Download/activate agents from sources
    agency source add       — Add a roster source
    agency mcp              — Serve MCP over stdio
    agency hook HOST        — Handle one native host hook event
    agency serve            — Start HTTP server
"""

from __future__ import annotations

import argparse
import getpass
import ipaddress
import json
import math
import os
import subprocess
import sys
import time
import urllib.request
import uuid
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

import yaml

from agency_runtime.core.config import (
    AgencyConfig,
    config_to_yaml,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.configuration import (
    apply_config_operations,
    read_config_revision,
    read_config_state,
    replace_config_document,
    resolve_config_path,
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
from agency_runtime.core.selector.explain import explain_route
from agency_runtime.core.selector.policy import load_policy
from agency_runtime.core.store.sqlite import Store


def _store(config: AgencyConfig | None = None) -> Store:
    if config:
        return Store(config.store.resolved_path())
    return Store()


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, sort_keys=True))


_REDACTED = "***REDACTED***"
_SECRET_KEY_PARTS = {
    "api_key",
    "access_token",
    "auth_token",
    "client_secret",
    "password",
    "refresh_token",
    "secret",
    "token",
}


def _configure_console_output() -> None:
    """Keep human CLI output usable on legacy Windows console encodings.

    Python can otherwise raise ``UnicodeEncodeError`` while printing the setup
    wizard's status and rule glyphs to a CP1252 console.  Reconfiguring only the
    error strategy preserves UTF-8 output where available and emits escaped
    Unicode on narrower consoles.  Protocol commands remain byte-for-byte
    unchanged when their streams already support UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            # Captured, detached, and application-owned streams may reject
            # reconfiguration.  Those streams retain their existing behavior.
            continue


def _is_secret_config_part(part: str) -> bool:
    normalized = part.strip().lower().replace("-", "_")
    if normalized.endswith("_env"):
        return False
    return normalized in _SECRET_KEY_PARTS or any(
        normalized.endswith(f"_{secret}") for secret in _SECRET_KEY_PARTS
    )


def _config_display_value(
    value: Any,
    *,
    path: tuple[str, ...] = (),
    raw: bool = False,
) -> Any:
    """Convert config objects to JSON-safe values and recursively redact."""
    if not raw and path and _is_secret_config_part(path[-1]):
        return _REDACTED if value not in (None, "") else value
    if is_dataclass(value) and not isinstance(value, type):
        return {
            item.name: _config_display_value(
                getattr(value, item.name),
                path=(*path, item.name),
                raw=raw,
            )
            for item in fields(value)
        }
    if isinstance(value, dict):
        return {
            str(key): _config_display_value(
                nested,
                path=(*path, str(key)),
                raw=raw,
            )
            for key, nested in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [
            _config_display_value(nested, path=(*path, str(index)), raw=raw)
            for index, nested in enumerate(value)
        ]
    return value


def _format_config_value(value: Any) -> str:
    if isinstance(value, (dict, list, tuple)) or (
        is_dataclass(value) and not isinstance(value, type)
    ):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _nested_config_value(data: Any, parts: Sequence[str]) -> Any:
    """Read a path from the raw YAML shape after policy enforcement."""
    current = data
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, (list, tuple)):
            current = current[int(part)]
        else:
            raise KeyError(".".join(parts))
    return current


def _is_loopback_url(value: Any) -> bool:
    try:
        hostname = urlsplit(str(value)).hostname
        if not hostname:
            return False
        if hostname.lower() == "localhost":
            return True
        return ipaddress.ip_address(hostname).is_loopback
    except ValueError:
        return False


def _enforce_local_only_config(data: dict[str, Any]) -> dict[str, Any]:
    """Make the local-only profile a write-time, no-remote invariant."""
    if str(data.get("profile", "standard")).strip().lower() != "local-only":
        return data

    ollama = data.get("ollama")
    if not isinstance(ollama, dict):
        ollama = {}
        data["ollama"] = ollama
    base_url = ollama.get("base_url", "http://127.0.0.1:11434")
    if not _is_loopback_url(base_url):
        base_url = "http://127.0.0.1:11434"

    judge = data.get("judge")
    if not isinstance(judge, dict):
        judge = {}
    judge_base = judge.get("base_url", "")
    judge_model = judge.get("model", "") if _is_loopback_url(judge_base) else ""
    model = str(ollama.get("model") or judge_model or "qwen3.5:2b")
    judge.update(
        {
            "model": model,
            "base_url": base_url,
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": True,
        }
    )
    data["judge"] = judge
    ollama.update({"enabled": True, "base_url": base_url, "model": model})
    data["providers"] = [
        {
            "name": "ollama",
            "type": "ollama",
            "model": model,
            "base_url": base_url,
            "api_key": "",
            "ollama_mode": True,
            "timeout": float(judge.get("timeout", 15.0)),
        }
    ]

    adapters = data.get("adapters")
    if not isinstance(adapters, dict):
        adapters = {}
        data["adapters"] = adapters
    for name in ("litellm", "hermes", "openclaw", "codex", "claude"):
        entry = adapters.get(name)
        if not isinstance(entry, dict):
            entry = {}
            adapters[name] = entry
        entry["enabled"] = "false"
    return data


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
    """Install, preview, or roll back host-native Agency Runtime bundles."""
    from agency_runtime.core.installer import (
        detect_installed_agents,
        install_agent_adapter,
        plan_agent_adapter,
        rollback_agent_adapter,
        seed_starter_roster,
    )
    from agency_runtime.core.dashboard_service import (
        install_dashboard_service,
        plan_dashboard_service,
    )
    from agency_runtime.core.dashboard_runtime import dashboard_service_reachable

    rollback_mode = bool(getattr(args, "rollback", False))
    dry_run = bool(getattr(args, "dry_run", False))
    backup = getattr(args, "backup", None)
    if rollback_mode and dry_run:
        raise ValueError("install --rollback and --dry-run are mutually exclusive")
    if backup and not rollback_mode:
        raise ValueError("install --backup requires --rollback")

    cfg = load_config()
    json_mode = bool(getattr(args, "json", False))

    if rollback_mode:
        if not args.agent or args.all:
            raise ValueError("install --rollback requires exactly one --agent")
        result = rollback_agent_adapter(args.agent, backup_path=backup)
        if json_mode:
            _print_json(result)
        elif result.get("ok"):
            print(f"✅ {args.agent}: rollback restored {result.get('restored_from')}")
            print(f"   Maturity: {result.get('maturity', 'unknown')}")
            if result.get("restart_required"):
                print(f"   Restart {args.agent} to load the restored integration.")
        else:
            print(f"❌ {args.agent}: {result.get('error', 'rollback failed')}")
        return int(result.get("exit_code", 0 if result.get("ok") else 1))

    requested_profile = args.profile or cfg.profile
    if args.profile and args.profile != cfg.profile:
        raise ValueError(
            f"install does not rewrite runtime policy: active profile is {cfg.profile!r}, "
            f"requested {args.profile!r}; run `agency configure --profile {args.profile}` first"
        )
    profile = get_profile(requested_profile)
    targets = (
        detect_installed_agents() if args.all else ([args.agent] if args.agent else [])
    )
    dashboard_opted_out = bool(getattr(args, "no_dashboard", False))
    if dry_run:
        plans = [plan_agent_adapter(host) for host in targets]
        host_plan_complete = (
            bool(plans)
            and all(plan.get("ok") and plan.get("executable") for plan in plans)
            if args.all
            else all(plan.get("ok") for plan in plans)
        )
        dashboard_plan = (
            {
                "ok": True,
                "exit_code": 0,
                "dry_run": True,
                "status": "opted_out",
                "changed": False,
            }
            if dashboard_opted_out
            else plan_dashboard_service(config_path=resolve_config_path())
        )
        plan_complete = host_plan_complete and bool(dashboard_plan.get("ok"))
        report = {
            "ok": plan_complete,
            "complete": plan_complete,
            "dry_run": True,
            "profile": profile.name,
            "starter_roster": {
                "action": "seed_missing_idempotently",
                "candidate_count": len(STARTER_ROSTER),
            },
            "detected_hosts": targets,
            "host_plans": plans,
            "dashboard": dashboard_plan,
        }
        if json_mode:
            _print_json(report)
        else:
            print(
                f"DRY RUN — profile={profile.name}; would idempotently seed up to {len(STARTER_ROSTER)} starter agents"
            )
            if not targets:
                print(
                    "No host adapters selected or discovered; no files or native state would change."
                )
            for plan in plans:
                print(
                    f"  {plan['host']}: {plan.get('plugin_path')} ({plan.get('native_lifecycle')})"
                )
                print(
                    f"    discovered={plan.get('host_discovered')} commands={plan.get('commands_will_run')}"
                )
                for step in plan.get("native_command_plan", []):
                    condition = (
                        f" [{step['condition']}]" if step.get("condition") else ""
                    )
                    print(f"    argv={step.get('argv')}{condition}")
                gate = plan.get("gateway_safety_gate")
                if gate is not None:
                    print(
                        f"    gateway={gate.get('state')} safe_to_mutate={gate.get('safe_to_mutate')}"
                    )
            if dashboard_opted_out:
                print("  dashboard: opted out; no service-manager query or mutation")
            else:
                print(
                    "  dashboard: "
                    f"{dashboard_plan.get('manager')} at {dashboard_plan.get('registration_path')}"
                )
                if dashboard_plan.get("error"):
                    print(f"    error={dashboard_plan['error']}")
        return 0 if plan_complete else 1

    if args.all and not targets:
        dashboard_result = {
            "ok": False,
            "exit_code": 1,
            "status": "not_attempted",
            "changed": False,
            "reason": "no supported hosts detected",
        }
        if json_mode:
            _print_json(
                {
                    "ok": False,
                    "complete": False,
                    "profile": profile.name,
                    "roster_added": 0,
                    "hosts": [],
                    "dashboard": dashboard_result,
                    "error": "No supported AI agent hosts detected",
                }
            )
        else:
            print("\n⚠️  No supported AI agent hosts detected.")
            print("   Install Hermes, OpenClaw, Codex, or Claude Code first.")
            print("   No roster or dashboard-service state was changed.")
        return 1

    store = _store(cfg)
    count = seed_starter_roster(store)
    host_results: list[dict[str, Any]] = []
    dashboard_result = (
        {
            "ok": True,
            "exit_code": 0,
            "status": "opted_out",
            "changed": False,
        }
        if dashboard_opted_out
        else install_dashboard_service(
            config_path=resolve_config_path(),
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    )

    if not json_mode:
        print(f"✅ Agency Runtime profile: {profile.name}")
        print(f"✅ Starter roster activated: {count} agents")
        print(f"   Config: {cfg.config_path or '(defaults only)'}")
        print(f"   Judge model: {cfg.judge.model} ({cfg.judge.base_url})")
        if dashboard_opted_out:
            print("   Dashboard service: opted out (--no-dashboard)")
        elif dashboard_result.get("ok"):
            print("✅ Dashboard service: installed for the current user")
            print("   Open it with: agency dashboard service open")
        else:
            print(
                f"❌ Dashboard service: {dashboard_result.get('error', 'installation failed')}"
            )

    if not json_mode and args.all:
        print(f"\n🔍 Detected {len(targets)} agent host(s): {', '.join(targets)}")
    for host in targets:
        result = install_agent_adapter(host, cfg)
        if args.all:
            result["complete"] = bool(
                result.get("ok")
                and result.get("status") == "registered"
                and result.get("registered") is True
            )
            if not result["complete"]:
                result.setdefault(
                    "warning",
                    "Detected host did not reach native registration; install --all is incomplete.",
                )
        host_results.append(result)
        if not json_mode:
            _print_install_result(host, result)

    if not targets and not json_mode:
        print(
            "\n💡 Run `agency install --all --dry-run` to preview discovered host integrations."
        )
        print("   Run `agency dashboard` to open the local operations dashboard.")
    if json_mode:
        complete = bool(dashboard_result.get("ok")) and all(
            result.get("complete", result.get("ok")) for result in host_results
        )
        _print_json(
            {
                "ok": complete,
                "complete": complete,
                "profile": profile.name,
                "roster_added": count,
                "hosts": host_results,
                "dashboard": dashboard_result,
            }
        )
    successful = bool(dashboard_result.get("ok")) and all(
        result.get("ok") for result in host_results
    )
    if args.all:
        successful = (
            bool(host_results)
            and successful
            and all(result.get("complete") for result in host_results)
        )
    return 0 if successful else 1


def _print_install_result(host: str, result: dict[str, Any]) -> None:
    """Print native installation maturity without overstating runtime load."""
    if result.get("ok"):
        marker = (
            "✅"
            if result.get("complete", result.get("status") == "registered")
            else "⚠️ "
        )
        print(
            f"{marker} {host}: {result.get('status', 'staged')} → {result.get('plugin_path', 'unknown path')}"
        )
        print(f"   Maturity: {result.get('maturity', 'unknown')}")
        if result.get("backup_path"):
            print(f"   Backup: {result['backup_path']}")
        if result.get("warning"):
            print(f"   Warning: {result['warning']}")
        if result.get("restart_required"):
            print(f"   Restart {host} to activate the native state.")
        return
    partial = (
        " (filesystem staged; native registration incomplete)"
        if result.get("partial")
        else ""
    )
    print(f"❌ {host}: {result.get('error', 'installation failed')}{partial}")
    if result.get("failed_step"):
        print(f"   Failed step: {result['failed_step']}")
    if result.get("backup_path"):
        print(f"   Backup retained: {result['backup_path']}")


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

    result = toggle_agency(
        agent,
        enabled=True,
        dry_run=bool(getattr(args, "dry_run", False)),
    )
    if getattr(args, "json", False):
        _print_json(result)
        return int(result.get("exit_code", 0 if result.get("ok") else 1))
    if result["ok"]:
        prefix = (
            "DRY RUN — would enable"
            if result.get("dry_run")
            else "✅ Agency Runtime enabled"
        )
        print(
            f"{prefix} for {agent} through {result.get('native_lifecycle', 'its native plugin lifecycle')}"
        )
        if result.get("restart_required"):
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

    result = toggle_agency(
        agent,
        enabled=False,
        dry_run=bool(getattr(args, "dry_run", False)),
    )
    if getattr(args, "json", False):
        _print_json(result)
        return int(result.get("exit_code", 0 if result.get("ok") else 1))
    if result["ok"]:
        prefix = (
            "DRY RUN — would disable"
            if result.get("dry_run")
            else "⏸️  Agency Runtime disabled"
        )
        print(
            f"{prefix} for {agent} through {result.get('native_lifecycle', 'its native plugin lifecycle')}"
        )
        if result.get("restart_required"):
            print(f"   Restart {agent} to take effect.")
    else:
        print(f"❌ {result['error']}")
    return 0 if result["ok"] else 1


# ── Configure wizard ─────────────────────────────────────────


def cmd_configure(args: argparse.Namespace) -> int:
    """Guided setup wizard or non-interactive config generation."""
    _configure_console_output()

    config_path = resolve_config_path()
    trusted_replacement = bool(args.force)

    if config_path.exists() and not args.force:
        print(f"Config already exists at {config_path}")
        if not args.non_interactive:
            resp = input("Overwrite? [y/N] ").strip().lower()
            if resp != "y":
                print("Aborted.")
                return 0
            trusted_replacement = True
        else:
            print("Use --force to overwrite in non-interactive mode.")
            return 1

    profile = args.profile or "standard"
    if not args.non_interactive and args.profile is None:
        profile = _prompt_install_profile()

    print("\nDetecting available providers...")
    detection = _detect_for_profile(profile)
    p = detection.providers
    a = detection.adapters

    print(
        f"  {'✅' if p.ollama_available else '❌'} Ollama: {p.ollama_base_url}"
        + (f" ({len(p.ollama_models)} models)" if p.ollama_models else "")
    )
    print(
        f"  {'✅' if p.openai_key else '❌'} OpenAI API key: {'found' if p.openai_key else 'not set'}"
    )
    print(
        f"  {'✅' if p.anthropic_key else '❌'} Anthropic API key: {'found' if p.anthropic_key else 'not set'}"
    )
    print(
        f"  {'✅' if p.litellm_available else '❌'} LiteLLM proxy: {p.litellm_base_url}"
    )
    print()
    print(f"  {'✅' if a.hermes else '❌'} Hermes adapter")
    print(f"  {'✅' if a.openclaw else '❌'} OpenClaw adapter")
    print(f"  {'✅' if a.codex else '❌'} Codex CLI")
    print(f"  {'✅' if a.claude else '❌'} Claude Code CLI")
    print()

    if args.non_interactive:
        config_data = generate_config_from_detection(detection, profile=profile)
    else:
        config_data = _interactive_wizard(detection, profile)
    config_data = _enforce_local_only_config(config_data)

    # Write config
    replace_config_document(
        config_data,
        expected_revision=(
            read_config_revision(config_path)
            if trusted_replacement
            else read_config_state(config_path).revision
        ),
        path=config_path,
        recover_invalid_existing=trusted_replacement,
    )

    print(f"\n✅ Config written to {config_path}")

    # Install starter roster
    reset_config_cache()
    cfg = load_config(reload=True)
    store = _store(cfg)
    count = _seed_starter_roster(store)
    print(f"✅ Starter roster installed: {count} agents")
    print(f"✅ SQLite database initialized: {cfg.store.resolved_path()}")
    print("\nNext steps:")
    print("  agency doctor              — verify everything is working")
    print('  agency search "code review" — test the selector')
    print('  agency route "review this PR" — see routing in action')
    return 0


def _prompt_install_profile() -> str:
    """Choose the network posture before any provider discovery occurs."""
    print("Step 1: Install Profile")
    print("━" * 40)
    print(
        "  [1] local-only — No remote network, no auto-sync, bundled roster only (safest)"
    )
    print("  [2] standard   — Network enabled, no auto-sync (recommended)")
    print("  [3] power      — Network enabled, manual sync")
    print("  [4] yolo       — Network enabled, trusted-source nightly auto-sync")
    profile_choice = _prompt_choice(4, default=2)
    return ["local-only", "standard", "power", "yolo"][profile_choice - 1]


def _detect_for_profile(profile: str):
    """Detect providers without contacting remote APIs for local-only setup."""
    if profile != "local-only":
        return detect_all()

    sentinel = object()
    remote_key_names = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    saved_keys = {name: os.environ.pop(name, sentinel) for name in remote_key_names}
    try:
        detection = detect_all()
    finally:
        for name, value in saved_keys.items():
            if value is not sentinel:
                os.environ[name] = str(value)
    # A mocked detector or future detector must not accidentally reintroduce
    # remote providers into the local-only wizard.
    detection.providers.openai_key_present = False
    detection.providers.openai_models.clear()
    detection.providers.anthropic_key_present = False
    return detection


def _interactive_wizard(detection, profile: str) -> dict[str, Any]:
    """Interactive wizard — prompts for each decision with full model discovery."""
    p = detection.providers

    print("Step 2: Judge Model")
    print("━" * 40)

    # ── Build provider menu ────────────────────────────────────
    # Each entry: (menu_label, handler_fn)
    # The handler returns a judge_cfg dict
    providers: list[tuple[str, str]] = []

    if profile == "local-only":
        provider_key = "ollama"
        judge_cfg = _pick_ollama_model(p)
    else:
        if p.ollama_available:
            n = len(p.ollama_models)
            providers.append(
                ("ollama", f"Ollama (free, local) — {n} model(s) available")
            )

        if p.openai_key_present:
            n = len(p.openai_models)
            suffix = f" — {n} model(s) discovered" if n else " (model list unavailable)"
            providers.append(("openai", f"OpenAI API (key detected){suffix}"))

        if p.anthropic_key_present:
            providers.append(("anthropic", "Anthropic API (key detected)"))

        if p.litellm_available:
            n = len(p.litellm_models)
            suffix = (
                f" — {n} model group(s) discovered"
                if n
                else " (model list unavailable)"
            )
            providers.append(("litellm", f"LiteLLM proxy{suffix}"))

        providers.append(
            (
                "custom",
                "Custom OpenAI-compatible endpoint (OpenRouter, Together, Groq, LM Studio, etc.)",
            )
        )

        print("\nWhich provider should the Agency selector use for routing?\n")
        for i, (_, label) in enumerate(providers, 1):
            print(f"  [{i}] {label}")

        choice_idx = _prompt_choice(len(providers), default=1) - 1
        provider_key = providers[choice_idx][0]

        # ── Per-provider model selection ──────────────────────
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

    # Step 3: Adapters
    print("\nStep 3: Host Adapters")
    print("━" * 40)
    a = detection.adapters
    adapters_cfg: dict[str, Any] = {}

    # LiteLLM adapter config
    litellm_detected = p.litellm_available
    icon = "✅" if litellm_detected else "❌"
    print(
        f"  {icon} LiteLLM proxy: {'detected' if litellm_detected else 'not detected'}"
    )
    litellm_skip = ["complexity_router", "auto_router/"]
    # If we chose LiteLLM as judge, add the model to skip_models to prevent recursion
    if judge_cfg.get("base_url") == p.litellm_base_url and judge_cfg.get("model"):
        if judge_cfg["model"] not in litellm_skip:
            litellm_skip.append(judge_cfg["model"])
    adapters_cfg["litellm"] = {
        "enabled": (
            "false"
            if profile == "local-only"
            else ("true" if litellm_detected else "auto")
        ),
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
            "enabled": (
                "false" if profile == "local-only" else ("true" if detected else "auto")
            )
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

    provider_type = {
        "ollama": "ollama",
        "anthropic": "anthropic",
        "litellm": "litellm",
    }.get(provider_key, "openai-compatible")
    provider_entry = {
        "name": provider_key,
        "type": provider_type,
        "model": judge_cfg.get("model", ""),
        "base_url": judge_cfg.get("base_url", ""),
        "api_key": judge_cfg.get("api_key", ""),
        "api_key_env": judge_cfg.get("api_key_env", ""),
        "ollama_mode": bool(judge_cfg.get("ollama_mode", False)),
        "timeout": float(judge_cfg.get("timeout", 15.0)),
    }

    config_data = {
        "providers": [provider_entry],
        "judge": judge_cfg,
        "ollama": {
            "enabled": p.ollama_available,
            "base_url": p.ollama_base_url,
        },
        "selector": {
            "min_confidence": 0.4,
            "max_user_msg_len": 4000,
            "trivial_msg_threshold": 12,
        },
        "store": {"db_path": "~/.agency-runtime/agency.db"},
        "server": {"host": "127.0.0.1", "port": 7800},
        "adapters": adapters_cfg,
        "profile": profile,
        "companion_policy_path": None,
    }
    config_data = _enforce_local_only_config(config_data)

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

    print("\nOpenAI models available:")
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

    print("\nAnthropic models:")
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
        key_choice = input(
            f"Press Enter to use ${key_env} env var, or type key directly: "
        ).strip()
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
        return sorted(
            [
                m.get("id", m.get("model", ""))
                for m in data.get("data", [])
                if m.get("id") or m.get("model")
            ]
        )
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
        print("  API key:      (stored in config)")
    else:
        print("  API key:      none (free/local)")
    print(f"  Ollama mode:  {j.get('ollama_mode', False)}")
    print(f"  Profile:      {config_data.get('profile', 'standard')}")


def _prompt_choice(max_val: int, default: int = 1) -> int:
    while True:
        raw = input("> ").strip()
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
    path = resolve_config_path()
    suffix = "" if path.exists() else " (not created; using bundled defaults)"
    print(f"{path}{suffix}")
    return 0


def cmd_config_get(args: argparse.Namespace) -> int:
    cfg = load_config()
    # Navigate dotted path: judge.model, ollama.enabled, etc.
    parts = args.key.split(".")
    val: Any = cfg
    for part in parts:
        if hasattr(val, part):
            val = getattr(val, part)
        elif isinstance(val, (list, tuple)):
            try:
                val = val[int(part)]
            except (IndexError, TypeError, ValueError):
                print(f"Key not found: {args.key}", file=sys.stderr)
                return 1
        elif hasattr(val, "__getitem__"):
            try:
                val = val[part]
            except (KeyError, TypeError):
                print(f"Key not found: {args.key}", file=sys.stderr)
                return 1
        else:
            print(f"Key not found: {args.key}", file=sys.stderr)
            return 1
    display = _config_display_value(
        val,
        path=tuple(parts),
        raw=bool(getattr(args, "raw", False)),
    )
    print(_format_config_value(display))
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    parts = args.key.split(".")
    if not all(parts):
        raise ValueError("config key must be a non-empty dotted path")
    is_secret = _is_secret_config_part(parts[-1])
    input_modes = sum(
        bool(value)
        for value in (
            getattr(args, "stdin", False),
            getattr(args, "prompt", False),
            getattr(args, "clear", False),
        )
    )
    if input_modes > 1:
        raise ValueError("--stdin, --prompt, and --clear are mutually exclusive")

    if getattr(args, "clear", False):
        if not is_secret or args.value is not None:
            raise ValueError("--clear is valid only for a secret key without a value")
        operation = {"op": "secret", "path": args.key, "action": "clear"}
    elif is_secret:
        if args.value is not None:
            raise ValueError(
                "secret values are not accepted as arguments; use --stdin or --prompt"
            )
        if getattr(args, "stdin", False):
            secret_value = sys.stdin.readline().rstrip("\r\n")
        elif getattr(args, "prompt", False):
            secret_value = getpass.getpass(f"New value for {args.key}: ")
        else:
            raise ValueError("secret updates require --stdin, --prompt, or --clear")
        operation = {
            "op": "secret",
            "path": args.key,
            "action": "replace",
            "value": secret_value,
        }
    else:
        if getattr(args, "clear", False) or getattr(args, "prompt", False):
            raise ValueError("--prompt and --clear are valid only for secret keys")
        if getattr(args, "stdin", False) and args.value is not None:
            raise ValueError("provide either a positional value or --stdin, not both")
        raw_value = sys.stdin.read() if getattr(args, "stdin", False) else args.value
        if raw_value is None:
            raise ValueError("config set requires a value or --stdin")
        try:
            parsed_value = yaml.safe_load(raw_value)
        except yaml.YAMLError as exc:
            raise ValueError("config value is not valid YAML") from exc
        if (
            args.key.startswith("adapters.")
            and args.key.endswith(".enabled")
            and isinstance(parsed_value, bool)
        ):
            parsed_value = "true" if parsed_value else "false"
        operation = {"op": "set", "path": args.key, "value": parsed_value}

    state = read_config_state()
    result = apply_config_operations(
        [operation],
        expected_revision=state.revision,
    )
    effective_value = _nested_config_value(result.state.effective, parts)
    display = _config_display_value(effective_value, path=tuple(parts), raw=False)
    notes: list[str] = []
    if result.policy_enforced:
        notes.append("local-only policy enforced")
    if args.key in result.state.environment_overrides:
        notes.append(
            f"effective value is overridden by {result.state.environment_overrides[args.key]}"
        )
    if result.restart_required:
        notes.append(f"restart required: {', '.join(result.restart_required)}")
    suffix = f" ({'; '.join(notes)})" if notes else ""
    print(f"Set {args.key} = {_format_config_value(display)}{suffix}")
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
    config_path = (
        Path(cfg.config_path)
        if cfg.config_path
        else Path.home() / ".agency-runtime" / "agency.yaml"
    )
    if config_path.exists():
        resp = (
            input(f"Delete {config_path} and reset to defaults? [y/N] ").strip().lower()
        )
        if resp != "y":
            print("Aborted.")
            return 0
        config_path.unlink()
    print("Config reset. Run `agency configure` to set up again.")
    return 0


# ── Sync ─────────────────────────────────────────────────────


def cmd_sync(args: argparse.Namespace) -> int:
    store = _store()
    sources = store.list_agent_sources()
    if not sources:
        print(
            "No enabled sources configured. Add one with: agency source add <url>",
            file=sys.stderr,
        )
        return 1
    if args.auto_approve:
        untrusted = [
            source
            for source in sources
            if not int(source.get("trusted_for_auto_approve") or 0)
        ]
        if untrusted:
            names = ", ".join(
                str(source.get("name") or source.get("url")) for source in untrusted
            )
            print(
                "Refusing --auto-approve because these sources are not trusted: "
                + names,
                file=sys.stderr,
            )
            print(
                "Mark an intended source with: agency source add <url> --trusted-for-auto-approve",
                file=sys.stderr,
            )
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
            errors.append(
                {"source": source["url"], "error": "source returned zero candidates"}
            )
            continue
        for agent in candidates:
            ok, reason = validate_agent(agent)
            if not ok:
                errors.append(
                    {
                        "source": source["url"],
                        "agent": agent.get("slug", ""),
                        "error": reason,
                    }
                )
                continue
            if args.dry_run:
                quarantined.append(agent["slug"])
            else:
                candidate_id = quarantine_candidate(agent, source["id"], store)
                quarantined.append(candidate_id)
    if args.dry_run:
        _print_json(
            {"dry_run": True, "valid_candidates": quarantined, "errors": errors}
        )
        return 0 if not errors else 2
    if args.auto_approve and errors:
        _print_json({"errors": errors})
        return 2
    if args.auto_approve and not quarantined:
        print(
            "Refusing --auto-approve because no candidates were quarantined",
            file=sys.stderr,
        )
        return 1
    diff = create_roster_diff(store, candidate_ids=quarantined)
    if args.review:
        _print_json(diff["diff"])
    if args.auto_approve:
        approve_snapshot(store, diff["snapshot_id"])
        activate_snapshot(store, diff["snapshot_id"])
        _print_json(
            {
                "snapshot_id": diff["snapshot_id"],
                "activated": True,
                "candidate_count": len(quarantined),
                "diff": diff["diff"],
            }
        )
    else:
        print(
            f"Created snapshot {diff['snapshot_id']} from {len(quarantined)} candidates"
        )
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
        print(
            f"{agent['slug']}\t{agent.get('name', '')}\t{agent.get('division', '')}\t{agent.get('description', '')}"
        )
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
            print(
                f"{agent['score']:.1f}\t{agent['slug']}\t{agent.get('name', '')}\t{agent.get('description', '')}"
            )
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    from agency_runtime.core.selector.candidate_narrow import pre_narrow
    from agency_runtime.core.selector.pipeline import route

    store = _store()
    catalog = store.get_active_roster_as_catalog()
    if not catalog:
        print("No active agents available", file=sys.stderr)
        return 1
    routing = route("cli", args.task, catalog, store=store)
    candidates, scores = pre_narrow(args.task, catalog, limit=args.limit)
    candidate_rows = [
        {**candidate, "score": round(float(score), 4)}
        for candidate, score in zip(candidates, scores)
    ]
    if args.json:
        _print_json(
            {
                "task": args.task,
                "routing": routing,
                "candidates": candidate_rows,
            }
        )
    else:
        selected = routing.get("selected_ids") or []
        if selected:
            print(f"selected: {', '.join(selected)}")
        else:
            print(f"selected: none (status={routing.get('status', 'unknown')})")
        print(
            f"confidence={float(routing.get('confidence', 0.0)):.3f} "
            f"source={routing.get('provider', 'deterministic')} "
            f"trace={routing.get('trace_id', '')}"
        )
        for agent in candidate_rows:
            print(f"candidate: {agent['slug']} score={agent['score']:.3f}")
        if routing.get("companion_actions"):
            print(f"companion actions: {', '.join(routing['companion_actions'])}")
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    store = _store()
    payload = explain_route(
        args.session_id,
        args.task,
        store.get_active_roster_as_catalog(),
        limit=args.limit,
        store=store,
    )
    _print_json(payload)
    return 0


def _run_command(command: list[str], *, timeout: float | None = None) -> int:
    if not command:
        print("No command supplied", file=sys.stderr)
        return 2
    proc = subprocess.run(command, text=True, timeout=timeout)  # noqa: S603
    return int(proc.returncode)


def _emit_delegate_result(
    args: argparse.Namespace, payload: dict[str, Any], *, stderr: str = ""
) -> int:
    if args.json:
        _print_json(payload)
    elif stderr:
        print(stderr, file=sys.stderr)
    elif payload.get("status") == "completed":
        output = payload.get("output")
        if isinstance(output, str) and output:
            print(output)
        elif output is not None:
            _print_json(output)
        print(f"Delegation completed via {payload.get('backend', 'unknown')}.")
    return int(payload.get("exit_code", 1))


def cmd_delegate(args: argparse.Namespace) -> int:
    from agency_runtime.core.delegation.backends import (
        BackendError,
        BackendRegistry,
        ClaudeExecBackend,
        CodexExecBackend,
        GenericCLIBackend,
        HermesDelegateBackend,
        OpenClawAgentBackend,
    )

    backend_name = args.backend
    task = args.task
    agent = args.agent
    if args.timeout is not None and (
        not math.isfinite(args.timeout) or args.timeout <= 0
    ):
        error = "--timeout must be a finite value greater than 0"
        return _emit_delegate_result(
            args,
            {"status": "error", "error": error, "exit_code": 2},
            stderr=error,
        )
    timeout = args.timeout if args.timeout is not None else 3600.0
    factories = {
        "codex": lambda: CodexExecBackend(timeout=timeout),
        "claude": lambda: ClaudeExecBackend(timeout=timeout),
        "hermes": lambda: HermesDelegateBackend(timeout=timeout),
        "openclaw": lambda: OpenClawAgentBackend(timeout=timeout),
        "generic": lambda: GenericCLIBackend(
            command=tuple(args.command or ()),
            timeout=timeout,
        ),
    }
    try:
        candidate = factories[backend_name]()
    except (KeyError, TypeError, ValueError) as exc:
        error = str(exc) or f"invalid backend configuration: {backend_name}"
        return _emit_delegate_result(
            args,
            {"status": "error", "error": error, "exit_code": 2},
            stderr=error,
        )

    store = _store()
    trace_id = f"cli-delegate-{uuid.uuid4()}"
    event_id = store.record_delegation(
        trace_id=trace_id,
        recommended_agent=agent or "",
        status="started",
        backend=backend_name,
    )
    payload = {
        "trace_id": trace_id,
        "event_id": event_id,
        "backend": backend_name,
        "agent": agent,
        "timeout_seconds": timeout,
    }

    try:
        selected = BackendRegistry([candidate]).select_backend(preferred=backend_name)
        result = selected.delegate(
            task=task,
            workdir=args.workdir,
            recommended_agent=agent or None,
        )
    except BackendError as exc:
        result = dict(exc.result)
        if not result:
            result = {
                "backend": backend_name,
                "status": "unavailable",
                "exit_code": 127,
                "error": str(exc),
            }
    except (TypeError, ValueError) as exc:
        result = {
            "backend": backend_name,
            "status": "error",
            "exit_code": 2,
            "error": str(exc),
        }

    status = str(result.get("status") or "failed")
    error = str(result.get("error") or "")
    if status == "completed":
        evidence_status = "completed"
        skip_reason = ""
    elif status in {"unavailable", "timed_out"}:
        evidence_status = "skipped"
        skip_reason = error or status
    else:
        evidence_status = "failed"
        skip_reason = ""
    store.update_delegation(
        event_id,
        status=evidence_status,
        backend=backend_name,
        error=error,
        skip_reason=skip_reason,
    )
    normalized = {**result, **payload, "status": evidence_status}
    if skip_reason:
        normalized["skip_reason"] = skip_reason
    return _emit_delegate_result(
        args, normalized, stderr=error if evidence_status != "completed" else ""
    )


def cmd_policy(args: argparse.Namespace) -> int:
    """Show the active companion policy and validate coverage against the roster."""
    policy = load_policy()
    actions = policy.get("actions", {})
    catalog = _store().get_active_roster_as_catalog()
    active_slugs = {a.get("slug") or a.get("agent_slug") or "" for a in catalog}

    if args.json:
        summary: dict[str, Any] = {
            "action_count": len(actions),
            "roster_count": len(active_slugs),
            "actions": {},
        }
        all_policy_slugs: list[str] = []
        for action, data in actions.items():
            always: list[str] = [
                str(i.get("slug", ""))
                for i in (data.get("always_include") or [])
                if isinstance(i, dict) and i.get("slug")
            ]
            conditional: list[str] = [
                str(i.get("slug", ""))
                for i in (data.get("conditional") or [])
                if isinstance(i, dict) and i.get("slug")
            ]
            all_policy_slugs += always + conditional
            summary["actions"][action] = {
                "always_include": always,
                "always_missing": [s for s in always if s not in active_slugs],
                "conditional": conditional,
                "conditional_missing": [
                    s for s in conditional if s not in active_slugs
                ],
            }
        unique = list(dict.fromkeys(all_policy_slugs))
        summary["unique_policy_slugs"] = len(unique)
        summary["all_missing"] = [s for s in unique if s not in active_slugs]
        _print_json(summary)
        return 0

    print(
        f"Companion policy: {len(actions)} broad actions, {len(active_slugs)} active roster agents\n"
    )
    for action, data in sorted(actions.items()):
        always_list: list[str] = [
            str(i.get("slug", ""))
            for i in (data.get("always_include") or [])
            if isinstance(i, dict) and i.get("slug")
        ]
        cond_list: list[str] = [
            str(i.get("slug", ""))
            for i in (data.get("conditional") or [])
            if isinstance(i, dict) and i.get("slug")
        ]
        always_missing: list[str] = [s for s in always_list if s not in active_slugs]
        cond_missing: list[str] = [s for s in cond_list if s not in active_slugs]
        status = "✅" if not always_missing else "❌"
        print(f"{status} {action}")
        print(f"   always_include ({len(always_list)}): {', '.join(always_list)}")
        if always_missing:
            print(f"   ⚠️  always_include MISSING: {', '.join(always_missing)}")
        print(
            f"   conditional ({len(cond_list)}): {', '.join(cond_list[:8])}{'…' if len(cond_list) > 8 else ''}"
        )
        if cond_missing:
            print(
                f"   ⚠️  conditional missing {len(cond_missing)}: {', '.join(cond_missing[:8])}{'…' if len(cond_missing) > 8 else ''}"
            )
    return 0


def cmd_eval_delegation(args: argparse.Namespace) -> int:
    from agency_runtime.core.evals.delegation import run_delegation_eval

    report = run_delegation_eval()
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"delegation eval {status}: {report['passed_count']} passed, {report['failed_count']} failed"
        )
        for case in report["cases"]:
            marker = "ok" if case["passed"] else "FAIL"
            detail = case.get("error") or case.get("detail") or ""
            print(f"{marker}\t{case['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_eval_routing(args: argparse.Namespace) -> int:
    """Run the versioned routing, policy, delegation, and latency gates."""
    from agency_runtime.core.evals.routing import run_routing_eval

    report = run_routing_eval(include_details=not args.no_details)
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        corpus = report["corpus"]
        print(
            f"routing eval {status}: corpus={corpus['version']} "
            f"routing={corpus['routing_cases']} policy={corpus['policy_cases']} "
            f"delegation={corpus['delegation_cases']}"
        )
        for gate in report["gates"]:
            marker = "ok" if gate["passed"] else "FAIL"
            print(
                f"{marker}\t{gate['area']}.{gate['metric']}="
                f"{gate['value']} {gate['operator']} {gate['threshold']}"
            )
    return 0 if report["passed"] else 1


def cmd_smoke(args: argparse.Namespace) -> int:
    from agency_runtime.core.smoke import run_smoke

    report = run_smoke(all_hosts=args.all)
    if args.json:
        _print_json(report)
    else:
        status = "passed" if report["passed"] else "failed"
        print(
            f"smoke {status}: {report['passed_count']} passed, {report['failed_count']} failed, {report['skipped_count']} skipped"
        )
        for check in report["checks"]:
            marker = {"pass": "ok", "skip": "skip", "fail": "FAIL"}.get(
                check["status"], check["status"]
            )
            detail = check.get("error") or check.get("detail") or ""
            print(f"{marker}\t{check['name']}\t{detail}")
    return 0 if report["passed"] else 1


def cmd_db_stats(args: argparse.Namespace) -> int:
    stats = _store().database_stats()
    if args.json:
        _print_json(stats)
    else:
        print(f"DB: {stats['db_path']}")
        print(
            f"Size: {stats['db_size_bytes']} bytes (wal={stats['wal_size_bytes']}, shm={stats['shm_size_bytes']})"
        )
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
        print(
            f"Size: {report['db_size_before_bytes']} -> {report['db_size_after_bytes']} bytes"
        )
        for table, detail in report["tables"].items():
            deleted = int(detail.get("deleted", 0))
            if deleted:
                print(f"{table}\tdeleted={deleted}")
        if not any(
            int(detail.get("deleted", 0)) for detail in report["tables"].values()
        ):
            print("No rows matched the retention policy.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from agency_runtime.server.http import serve

    serve()
    return 0


def cmd_mcp(args: argparse.Namespace) -> int:
    from agency_runtime.server.mcp import run_stdio

    store = Store(args.db) if args.db else None
    return run_stdio(store=store)


def cmd_hook(args: argparse.Namespace) -> int:
    from agency_runtime.adapters.hooks import run_hook_stdio

    store = Store(args.db) if args.db else None
    return run_hook_stdio(args.host, store=store)


def cmd_dashboard(args: argparse.Namespace) -> int:
    from agency_runtime.server.dashboard import run_dashboard

    run_dashboard(
        port=args.port,
        db_path=args.db,
        open_browser=not args.no_open,
        service_mode=bool(getattr(args, "service_mode", False)),
        config_path=getattr(args, "config", None),
    )
    return 0


def _wait_dashboard_ready(timeout_seconds: float = 8.0) -> bool:
    from agency_runtime.core.dashboard_runtime import dashboard_service_reachable

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if dashboard_service_reachable(timeout=0.5):
            return True
        time.sleep(0.1)
    return False


def cmd_dashboard_service(args: argparse.Namespace) -> int:
    from agency_runtime.core.dashboard_runtime import (
        dashboard_service_reachable,
        open_dashboard_service,
    )
    from agency_runtime.core.dashboard_service import (
        inspect_dashboard_service,
        install_dashboard_service,
        plan_dashboard_service,
        restart_dashboard_service,
        start_dashboard_service,
        stop_dashboard_service,
        uninstall_dashboard_service,
    )

    action = args.dashboard_service_action
    common = {"config_path": resolve_config_path()}
    if action == "open":
        result = open_dashboard_service(open_browser=not args.no_open)
    elif action == "status":
        result = inspect_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
        )
    elif action == "install" and args.dry_run:
        result = plan_dashboard_service(**common)
    elif action == "install":
        result = install_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    elif action == "start":
        result = start_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    elif action == "stop":
        result = stop_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
        )
    elif action == "restart":
        result = restart_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
            readiness_probe=_wait_dashboard_ready,
        )
    elif action == "uninstall":
        result = uninstall_dashboard_service(
            **common,
            reachability_probe=dashboard_service_reachable,
        )
    else:  # parser choices make this defensive only
        raise ValueError(f"unknown dashboard service action: {action}")

    if args.json:
        _print_json(result)
    elif result.get("ok"):
        status = result.get("status") or result.get("action") or action
        print(f"✅ Dashboard service {status}")
        if action == "open":
            print(f"   {result.get('url')}")
        elif action in {"install", "start", "restart"}:
            print("   Open it with: agency dashboard service open")
        if result.get("reachable") is False:
            print(
                "   Warning: registration exists, but the dashboard is not reachable."
            )
    else:
        print(
            f"❌ Dashboard service {action}: {result.get('error', 'operation failed')}"
        )
    return int(result.get("exit_code", 0 if result.get("ok") else 1))


def cmd_codex_exec(args: argparse.Namespace) -> int:
    return _run_command(["codex", "exec", *args.args])


def cmd_run(args: argparse.Namespace) -> int:
    return _run_command(args.args)


# ── Parser ───────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agency", description="Agency Runtime Control Plane"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # install
    install = sub.add_parser(
        "install", help="Install Agency Runtime — seed roster + wire into agent hosts"
    )
    install.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=None,
        help="Verify the already-configured profile; use `agency configure` to change it",
    )
    install_target = install.add_mutually_exclusive_group()
    install_target.add_argument(
        "--all",
        action="store_true",
        help="Auto-detect and wire into every AI agent host found",
    )
    install_target.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude"],
        default=None,
        help="Wire into a specific agent host",
    )
    install_action = install.add_mutually_exclusive_group()
    install_action.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a write-free roster and native host plan",
    )
    install_action.add_argument(
        "--rollback",
        action="store_true",
        help="Restore the latest retained backup for --agent",
    )
    install.add_argument(
        "--backup",
        default=None,
        help="Specific retained backup to restore with --rollback",
    )
    install.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Do not register or start the optional per-user dashboard service",
    )
    install.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    install.set_defaults(func=cmd_install)

    # on/off toggle
    on_p = sub.add_parser("on", help="Enable Agency Runtime for a host")
    on_p.add_argument(
        "--agent", choices=["hermes", "openclaw", "codex", "claude"], default=None
    )
    on_p.add_argument("--dry-run", action="store_true")
    on_p.add_argument("--json", action="store_true")
    on_p.set_defaults(func=cmd_on)

    off_p = sub.add_parser("off", help="Disable Agency Runtime for a host")
    off_p.add_argument(
        "--agent", choices=["hermes", "openclaw", "codex", "claude"], default=None
    )
    off_p.add_argument("--dry-run", action="store_true")
    off_p.add_argument("--json", action="store_true")
    off_p.set_defaults(func=cmd_off)

    # configure
    configure = sub.add_parser(
        "configure", help="Guided setup wizard — writes agency.yaml"
    )
    configure.add_argument(
        "--non-interactive",
        action="store_true",
        help="Write detected config without prompts",
    )
    configure.add_argument("--profile", choices=sorted(PROFILES), default=None)
    configure.add_argument(
        "--force", action="store_true", help="Overwrite existing config"
    )
    configure.set_defaults(func=cmd_configure)

    # doctor
    doctor = sub.add_parser(
        "doctor", help="Check DB, config, providers, and adapter availability"
    )
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
    config_get.add_argument("--raw", action="store_true", help="Show secret values")
    config_get.set_defaults(func=cmd_config_get)

    config_set = config_sub.add_parser("set", help="Set a config value")
    config_set.add_argument("key", help="Dotted key (e.g. judge.model)")
    config_set.add_argument(
        "value", nargs="?", help="YAML value to set (never use for secrets)"
    )
    config_input = config_set.add_mutually_exclusive_group()
    config_input.add_argument(
        "--stdin", action="store_true", help="Read the value from standard input"
    )
    config_input.add_argument(
        "--prompt", action="store_true", help="Prompt without echo for a secret value"
    )
    config_input.add_argument(
        "--clear", action="store_true", help="Clear a stored secret"
    )
    config_set.set_defaults(func=cmd_config_set)

    config_validate = config_sub.add_parser(
        "validate", help="Validate config + reachability"
    )
    config_validate.set_defaults(func=cmd_config_validate)

    config_reset = config_sub.add_parser("reset", help="Reset to defaults")
    config_reset.set_defaults(func=cmd_config_reset)

    # sync
    sync = sub.add_parser(
        "sync", help="Download sources into quarantine and create a roster snapshot"
    )
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
    roster_diff = roster_sub.add_parser(
        "diff", help="Create/show diff for quarantined candidates"
    )
    roster_diff.add_argument("--json", action="store_true")
    roster_diff.set_defaults(func=cmd_roster_diff)
    roster_approve = roster_sub.add_parser("approve", help="Approve snapshot")
    roster_approve.add_argument("snapshot_id")
    roster_approve.set_defaults(func=cmd_roster_approve)
    roster_activate = roster_sub.add_parser(
        "activate", help="Activate approved snapshot"
    )
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

    # policy
    policy_p = sub.add_parser(
        "policy",
        help="Show companion policy and validate coverage against active roster",
    )
    policy_p.add_argument("--json", action="store_true")
    policy_p.set_defaults(func=cmd_policy)

    # explain
    explain = sub.add_parser(
        "explain", help="Explain why specialists were selected for a task"
    )
    explain.add_argument("task")
    explain.add_argument(
        "--session-id", default="", help="Session id for cache/stickiness context"
    )
    explain.add_argument(
        "--limit", type=int, default=10, help="Number of candidates to include"
    )
    explain.set_defaults(func=cmd_explain)

    # delegate
    delegate = sub.add_parser("delegate", help="Delegate a task to a backend")
    delegate.add_argument(
        "--backend",
        choices=["codex", "claude", "hermes", "openclaw", "generic"],
        default="generic",
    )
    delegate.add_argument("--agent", default="")
    delegate.add_argument("--task", required=True)
    delegate.add_argument(
        "--workdir",
        default=None,
        help="Existing working directory for the delegated host",
    )
    delegate.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Stop waiting after N seconds and mark the delegation skipped",
    )
    delegate.add_argument(
        "--json", action="store_true", help="Print machine-readable delegation result"
    )
    delegate.add_argument(
        "--command",
        nargs=argparse.REMAINDER,
        default=[],
        help="Explicit argv for the generic backend; place this option last",
    )
    delegate.set_defaults(func=cmd_delegate)

    # eval
    eval_p = sub.add_parser("eval", help="Run deterministic eval suites")
    eval_sub = eval_p.add_subparsers(dest="eval_command", required=True)
    eval_delegation = eval_sub.add_parser(
        "delegation", help="Run delegation lifecycle/evidence evals"
    )
    eval_delegation.add_argument("--json", action="store_true")
    eval_delegation.set_defaults(func=cmd_eval_delegation)
    eval_routing = eval_sub.add_parser(
        "routing",
        help="Run versioned routing, policy, delegation, and latency gates",
    )
    eval_routing.add_argument("--json", action="store_true")
    eval_routing.add_argument(
        "--no-details",
        action="store_true",
        help="Omit per-case details from the report",
    )
    eval_routing.set_defaults(func=cmd_eval_routing)

    # smoke
    smoke = sub.add_parser("smoke", help="Run deterministic local smoke checks")
    smoke.add_argument(
        "--all",
        action="store_true",
        help="Smoke-test every supported generated host plugin",
    )
    smoke.add_argument("--json", action="store_true")
    smoke.set_defaults(func=cmd_smoke)

    # db
    db_p = sub.add_parser("db", help="Inspect and trim the SQLite store")
    db_sub = db_p.add_subparsers(dest="db_command", required=True)
    db_stats = db_sub.add_parser("stats", help="Show row counts and file sizes")
    db_stats.add_argument("--json", action="store_true")
    db_stats.set_defaults(func=cmd_db_stats)
    db_trim = db_sub.add_parser("trim", help="Trim append-only runtime/audit tables")
    db_trim.add_argument(
        "--older-than-days",
        type=int,
        default=None,
        help="Delete runtime rows older than N days",
    )
    db_trim.add_argument(
        "--keep-last",
        type=int,
        default=None,
        help="Keep only the newest N rows per runtime table",
    )
    db_trim.add_argument(
        "--dry-run",
        action="store_true",
        help="Report rows that would be deleted without changing the DB",
    )
    db_trim.add_argument(
        "--no-vacuum", action="store_true", help="Skip VACUUM after deleting rows"
    )
    db_trim.add_argument("--json", action="store_true")
    db_trim.set_defaults(func=cmd_db_trim)

    # Native machine protocols.  Both use stdin/stdout and therefore never
    # print human-oriented status text from the command wrapper.
    mcp = sub.add_parser("mcp", help="Serve MCP over stdin/stdout")
    mcp.add_argument("--db", default=None, help="SQLite database path")
    mcp.set_defaults(func=cmd_mcp)

    hook = sub.add_parser("hook", help="Handle one native host hook event")
    hook.add_argument("host", choices=["codex", "claude"])
    hook.add_argument("--db", default=None, help="SQLite database path")
    hook.set_defaults(func=cmd_hook)

    # serve
    serve_p = sub.add_parser("serve", help="Start HTTP server")
    serve_p.set_defaults(func=cmd_serve)

    dashboard = sub.add_parser(
        "dashboard", help="Open the secure local operations dashboard"
    )
    dashboard.add_argument(
        "--port",
        type=int,
        default=0,
        help="Loopback port (default: choose a free port)",
    )
    dashboard.add_argument("--db", default=None, help="SQLite database path")
    dashboard.add_argument(
        "--no-open", action="store_true", help="Do not open a web browser"
    )
    dashboard.add_argument(
        "--service-mode", action="store_true", help=argparse.SUPPRESS
    )
    dashboard.add_argument("--config", default=None, help=argparse.SUPPRESS)
    dashboard_sub = dashboard.add_subparsers(dest="dashboard_command")
    dashboard_service = dashboard_sub.add_parser(
        "service",
        help="Manage the optional per-user dashboard service",
    )
    dashboard_service_sub = dashboard_service.add_subparsers(
        dest="dashboard_service_action",
        required=True,
    )
    for action in ("status", "start", "stop", "restart", "uninstall"):
        action_parser = dashboard_service_sub.add_parser(action)
        action_parser.add_argument("--json", action="store_true")
        action_parser.set_defaults(func=cmd_dashboard_service)
    dashboard_service_install = dashboard_service_sub.add_parser("install")
    dashboard_service_install.add_argument("--dry-run", action="store_true")
    dashboard_service_install.add_argument("--json", action="store_true")
    dashboard_service_install.set_defaults(func=cmd_dashboard_service)
    dashboard_service_open = dashboard_service_sub.add_parser("open")
    dashboard_service_open.add_argument("--no-open", action="store_true")
    dashboard_service_open.add_argument("--json", action="store_true")
    dashboard_service_open.set_defaults(func=cmd_dashboard_service)
    dashboard.set_defaults(func=cmd_dashboard)

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
    _configure_console_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (KeyError, ValueError, RuntimeError) as exc:
        print(f"agency: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
