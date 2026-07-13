"""Interactive provider and profile configuration wizard."""

from __future__ import annotations

import getpass
import os
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.config import (
    MAX_PROVIDER_CHAIN_ENTRIES,
    ProviderEntry,
    is_safe_credential_url,
)
from agency_runtime.core.detect import (
    ProviderDetection,
    detect_all,
    generate_config_from_detection,
)
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.provider_validation import validate_provider

from ._common import (
    enforce_local_only_config as _enforce_local_only_config,
)
from ._common import (
    is_loopback_url as _is_loopback_url,
)


@dataclass(frozen=True, slots=True)
class WizardDependencies:
    """Patchable network, environment, and validation boundaries."""

    detect: Callable[[], Any] = detect_all
    secret_prompt: Callable[[str], str] = getpass.getpass
    open_url: Callable[..., Any] = open_no_redirect
    provider_validator: Callable[..., Any] = validate_provider
    model_fetcher: Callable[[str, str | None], list[str]] | None = None


DEFAULT_DEPENDENCIES = WizardDependencies()

MAX_MODEL_DISCOVERY_BYTES = 1024 * 1024
MAX_DISCOVERED_MODELS = 1000
MAX_MODEL_ID_CHARS = 512


def _models(
    base_url: str,
    api_key: str | None,
    dependencies: WizardDependencies,
) -> list[str]:
    if dependencies.model_fetcher is not None:
        return dependencies.model_fetcher(base_url, api_key)
    return _fetch_models_custom(base_url, api_key, dependencies=dependencies)


def _prompt_install_profile() -> str:
    """Choose the network posture before any provider discovery occurs."""
    print("Step 1: Install Profile")
    print("━" * 40)
    print("  [1] local-only — No remote network, no auto-sync, bundled roster only (safest)")
    print("  [2] standard   — Network enabled, no auto-sync (recommended)")
    print("  [3] power      — Network enabled, manual sync")
    print("  [4] yolo       — Network enabled, trusted-source nightly auto-sync")
    profile_choice = _prompt_choice(4, default=2)
    return ["local-only", "standard", "power", "yolo"][profile_choice - 1]


def _detect_for_profile(
    profile: str,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
):
    """Detect providers without contacting remote APIs for local-only setup."""
    if profile != "local-only":
        return dependencies.detect()

    sentinel = object()
    remote_key_names = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")
    saved_keys = {name: os.environ.pop(name, sentinel) for name in remote_key_names}
    try:
        detection = dependencies.detect()
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


def _interactive_wizard(
    detection,
    profile: str,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Interactive wizard — prompts for each decision with full model discovery."""
    p = detection.providers

    print("Step 2: Judge Model")
    print("━" * 40)

    generated = generate_config_from_detection(detection, profile=profile)
    provider_entries = _guided_provider_chain(
        detection,
        profile,
        dependencies=dependencies,
    )
    judge_cfg = _legacy_judge_from_chain(
        provider_entries,
        dict(generated.get("judge", {})),
    )

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
    if (
        judge_cfg.get("base_url") == p.litellm_base_url
        and judge_cfg.get("model")
        and judge_cfg["model"] not in litellm_skip
    ):
        litellm_skip.append(judge_cfg["model"])
    adapters_cfg["litellm"] = {
        "enabled": (
            "false" if profile == "local-only" else ("true" if litellm_detected else "auto")
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
            "enabled": ("false" if profile == "local-only" else ("true" if detected else "auto"))
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

    for provider in provider_entries:
        provider["timeout"] = timeout

    config_data = {
        "providers": provider_entries,
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


def _legacy_judge_from_chain(
    providers: list[dict[str, Any]],
    fallback: dict[str, Any],
) -> dict[str, Any]:
    """Mirror the first HTTP provider for backward-compatible judge settings."""

    for provider in providers:
        if provider.get("type") == "cli":
            continue
        return {
            "model": provider.get("model", ""),
            "base_url": provider.get("base_url", ""),
            "api_key": provider.get("api_key", ""),
            "api_key_env": provider.get("api_key_env", ""),
            "ollama_mode": bool(provider.get("ollama_mode", False)),
        }
    if providers:
        return {
            "model": "",
            "base_url": "",
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": False,
        }
    return fallback


def _provider_entry(
    name: str,
    provider_type: str,
    judge: dict[str, Any],
    *,
    transport: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "type": provider_type,
        "transport": transport,
        "model": judge.get("model", ""),
        "base_url": judge.get("base_url", ""),
        "api_key": judge.get("api_key", ""),
        "api_key_env": judge.get("api_key_env", ""),
        "ollama_mode": bool(judge.get("ollama_mode", False)),
        "timeout": float(judge.get("timeout", 15.0)),
    }


def _new_provider_entry(
    detection,
    profile: str,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any] | None:
    p = detection.providers
    if profile == "local-only":
        choices: list[tuple[str, str]] = [
            ("ollama", "Ollama (local)"),
            ("custom", "Custom literal-loopback OpenAI-compatible endpoint"),
        ]
    else:
        choices = [
            ("openai", "OpenAI API"),
            ("anthropic", "Anthropic API"),
        ]
        if p.ollama_available:
            choices.insert(0, ("ollama", "Ollama (local)"))
        if p.litellm_available:
            choices.append(("litellm", "LiteLLM proxy"))
        for transport in ("codex", "claude"):
            status = detection.cli_providers.get(transport)
            if status is not None and status.installed:
                state = "usable" if status.usable else "authentication required"
                choices.append((f"cli:{transport}", f"{transport.title()} CLI ({state})"))
        choices.append(("custom", "Custom OpenAI-compatible endpoint"))

    print("\nAdd provider:")
    for index, (_, label) in enumerate(choices, start=1):
        print(f"  [{index}] {label}")
    print(f"  [{len(choices) + 1}] Cancel")
    selected = _prompt_choice(len(choices) + 1, default=len(choices) + 1)
    if selected > len(choices):
        return None
    provider_key = choices[selected - 1][0]
    if provider_key == "ollama":
        return _provider_entry("ollama", "ollama", _pick_ollama_model(p))
    if provider_key == "openai":
        return _provider_entry(
            "openai",
            "openai-compatible",
            _pick_openai_model(p, dependencies=dependencies),
        )
    if provider_key == "anthropic":
        return _provider_entry(
            "anthropic",
            "anthropic",
            _pick_anthropic_model(dependencies=dependencies),
        )
    if provider_key == "litellm":
        return _provider_entry(
            "litellm",
            "litellm",
            _pick_litellm_model(p, dependencies=dependencies),
        )
    if provider_key.startswith("cli:"):
        transport = provider_key.split(":", 1)[1]
        model = input(f"Model override for {transport} (blank uses CLI default): ").strip()
        return _provider_entry(
            f"{transport}-cli",
            "cli",
            {"model": model},
            transport=transport,
        )
    custom = _pick_custom_endpoint(dependencies=dependencies)
    if profile == "local-only" and not _is_loopback_url(custom.get("base_url", "")):
        print("  Local-only providers must use a literal loopback endpoint.")
        return None
    custom_name = input("Provider name [custom]: ").strip() or "custom"
    return _provider_entry(custom_name, "openai-compatible", custom)


def _guided_provider_chain(
    detection,
    profile: str,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> list[dict[str, Any]]:
    """Edit an ordered provider chain with add, move, and remove actions."""

    suggested = generate_config_from_detection(detection, profile=profile)
    providers = [dict(item) for item in suggested.get("providers", [])]
    while True:
        print("\nOrdered provider fallback:")
        if providers:
            for index, provider in enumerate(providers, start=1):
                transport = f":{provider.get('transport')}" if provider.get("transport") else ""
                print(
                    f"  [{index}] {safe_display_token(provider.get('name'))} "
                    f"({safe_display_token(provider.get('type'))}"
                    f"{safe_display_token(transport)})"
                )
        else:
            print("  (empty — add at least one provider)")
        print("\n  [1] Add provider")
        print("  [2] Move provider")
        print("  [3] Remove provider")
        print("  [4] Done")
        action = _prompt_choice(4, default=4 if providers else 1)
        if action == 1:
            if len(providers) >= MAX_PROVIDER_CHAIN_ENTRIES:
                print(
                    f"  Provider chains support at most "
                    f"{MAX_PROVIDER_CHAIN_ENTRIES} entries; remove one first."
                )
                continue
            entry = _new_provider_entry(
                detection,
                profile,
                dependencies=dependencies,
            )
            if entry is None:
                continue
            names = {str(item.get("name", "")).casefold() for item in providers}
            if str(entry.get("name", "")).casefold() in names:
                print("  That provider name already exists; remove it or choose another name.")
                continue
            providers.append(entry)
        elif action == 2:
            if len(providers) < 2:
                print("  Add at least two providers before reordering.")
                continue
            source = _prompt_choice(len(providers), default=1)
            destination = _prompt_choice(len(providers), default=source)
            item = providers.pop(source - 1)
            providers.insert(destination - 1, item)
        elif action == 3:
            if not providers:
                continue
            providers.pop(_prompt_choice(len(providers), default=len(providers)) - 1)
        elif providers:
            return providers


def _validate_interactive_provider_chain(
    providers: list[dict[str, Any]],
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> bool:
    """Validate every entry independently and identify its ordered position."""

    all_valid = True
    print("\nValidating provider fallback chain...")
    for index, raw in enumerate(providers):
        try:
            provider = ProviderEntry(**raw)
            result = dependencies.provider_validator(
                provider,
                timeout=min(provider.timeout, 5.0),
            )
        except (TypeError, ValueError) as exc:
            print(f"  ❌ providers.{index}: invalid configuration ({type(exc).__name__})")
            all_valid = False
            continue
        if result.usable:
            print(f"  ✅ providers.{index} ({safe_display_token(provider.name)}): usable")
        else:
            print(
                f"  ❌ providers.{index} ({safe_display_token(provider.name)}): "
                f"{safe_display_token(result.reason or 'unavailable')}"
            )
            all_valid = False
    return all_valid


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
    visible_models = p.ollama_models[:15]
    for i, model in enumerate(visible_models, 1):
        print(f"  [{i}] {model}")
    if len(p.ollama_models) > 15:
        print(f"  ... and {len(p.ollama_models) - 15} more")
    custom_choice = len(visible_models) + 1
    print(f"  [{custom_choice}] Enter custom model name")

    choice = _prompt_choice(custom_choice, default=1)
    if choice <= len(visible_models):
        model = visible_models[choice - 1]
    else:
        model = input("Model name: ").strip() or "qwen3.5:2b"

    return {
        "model": model,
        "base_url": p.ollama_base_url,
        "api_key": "",
        "ollama_mode": True,
    }


def _pick_openai_model(
    p: ProviderDetection,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Let user pick from discovered OpenAI models or enter a custom one."""
    from agency_runtime.core.detect import _OPENAI_SUGGESTIONS

    base_url = "https://api.openai.com/v1"
    auth, resolved_key = _prompt_provider_auth(
        default_env="OPENAI_API_KEY",
        base_url=base_url,
        dependencies=dependencies,
    )
    discovered_models = (
        _models(base_url, resolved_key, dependencies) if resolved_key else p.openai_models
    )

    # Merge discovered + suggestions, dedup, preserve order
    all_models: list[str] = []
    seen = set()
    for m in discovered_models + _OPENAI_SUGGESTIONS:
        if m not in seen:
            all_models.append(m)
            seen.add(m)

    print("\nOpenAI models available:")
    visible_models = all_models[:15]
    for i, model in enumerate(visible_models, 1):
        discovered = "✅" if model in discovered_models else "  "
        print(f"  [{i}] {discovered} {model}")
    if len(all_models) > 15:
        print(f"  ... and {len(all_models) - 15} more")
    custom_choice = len(visible_models) + 1
    print(f"  [{custom_choice}] Enter custom model name")

    choice = _prompt_choice(custom_choice, default=1)
    if choice <= len(visible_models):
        model = visible_models[choice - 1]
    else:
        model = input("Model name (e.g. gpt-4o-mini): ").strip()
        if not model:
            model = "gpt-4o-mini"

    return {
        "model": model,
        "base_url": base_url,
        "ollama_mode": False,
        **auth,
    }


def _pick_anthropic_model(
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Let user pick an Anthropic model."""
    from agency_runtime.core.detect import _ANTHROPIC_SUGGESTIONS

    auth, _ = _prompt_provider_auth(
        default_env="ANTHROPIC_API_KEY",
        base_url="https://api.anthropic.com/v1",
        dependencies=dependencies,
    )
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
        "ollama_mode": False,
        **auth,
    }


def _pick_litellm_model(
    p: ProviderDetection,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
    """Let user pick from discovered LiteLLM model groups or enter one."""
    auth, resolved_key = _prompt_provider_auth(
        default_env="LITELLM_API_KEY",
        base_url=p.litellm_base_url,
        dependencies=dependencies,
    )
    models = (
        _models(p.litellm_base_url, resolved_key, dependencies)
        if resolved_key
        else p.litellm_models
    )
    if models:
        print(f"\nLiteLLM model groups available ({len(models)}):")
        visible_models = models[:15]
        for i, model in enumerate(visible_models, 1):
            print(f"  [{i}] {model}")
        if len(models) > 15:
            print(f"  ... and {len(models) - 15} more")
        custom_choice = len(visible_models) + 1
        print(f"  [{custom_choice}] Enter custom model group name")

        choice = _prompt_choice(custom_choice, default=1)
        if choice <= len(visible_models):
            model = visible_models[choice - 1]
        else:
            model = input("Model group name: ").strip()
    else:
        print("\nCouldn't discover LiteLLM models (proxy may need an API key).")
        print("Enter your LiteLLM model group name.")
        print("Common patterns: task-general, gpt-4o-mini, claude-sonnet, etc.")
        model = input("Model group name: ").strip()
        if not model:
            model = "task-general"

    return {
        "model": model,
        "base_url": p.litellm_base_url,
        "ollama_mode": False,
        **auth,
    }


def _prompt_provider_auth(
    *,
    default_env: str,
    base_url: str,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> tuple[dict[str, str], str]:
    """Choose env, hidden direct, or loopback-only unauthenticated access."""

    loopback = _is_loopback_url(base_url)
    print("\nAuthentication:")
    print(f"  [1] Environment variable reference [{default_env}]")
    print("  [2] Direct key (hidden; stored in owner-only config)")
    if loopback:
        print("  [3] No key (literal loopback endpoint only)")
    choice = _prompt_choice(3 if loopback else 2, default=1)
    if choice == 2:
        direct = dependencies.secret_prompt("API key: ").strip()
        if not direct:
            raise ValueError("direct API key must not be empty")
        return {"api_key": direct}, direct
    if choice == 3 and loopback:
        return {"api_key": ""}, ""
    env_name = input(f"Environment variable name [{default_env}]: ").strip()
    env_name = env_name or default_env
    return {"api_key_env": env_name}, os.environ.get(env_name, "")


def _pick_custom_endpoint(
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> dict[str, Any]:
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
        default_key_env = ""

    auth, resolved_key = _prompt_provider_auth(
        default_env=default_key_env or "PROVIDER_API_KEY",
        base_url=base_url,
        dependencies=dependencies,
    )

    # Discover only after authentication is available to the request.
    print(f"\nDiscovering models at {base_url}...")
    models = _models(base_url, resolved_key, dependencies)

    if models:
        print(f"Found {len(models)} models:")
        visible_models = models[:15]
        for i, model in enumerate(visible_models, 1):
            print(f"  [{i}] {model}")
        if len(models) > 15:
            print(f"  ... and {len(models) - 15} more")
        custom_choice = len(visible_models) + 1
        print(f"  [{custom_choice}] Enter custom model name")

        model_choice = _prompt_choice(custom_choice, default=1)
        if model_choice <= len(visible_models):
            model = visible_models[model_choice - 1]
        else:
            model = input("Model name: ").strip()
    else:
        print("Could not discover models (endpoint may need an API key).")
        model = input("Enter model name: ").strip()

    result: dict[str, Any] = {
        "model": model,
        "base_url": base_url,
        "ollama_mode": False,
        **auth,
    }
    return result


def _fetch_models_custom(
    base_url: str,
    api_key: str | None = None,
    *,
    dependencies: WizardDependencies = DEFAULT_DEPENDENCIES,
) -> list[str]:
    """Fetch models from a custom OpenAI-compatible endpoint."""
    if api_key and not is_safe_credential_url(base_url):
        return []
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/models",
            headers=headers,
        )
        with dependencies.open_url(req, timeout=5) as resp:
            raw = resp.read(MAX_MODEL_DISCOVERY_BYTES + 1)
        if len(raw) > MAX_MODEL_DISCOVERY_BYTES:
            return []
        data = safe_load_bounded_json(
            raw,
            maximum_bytes=MAX_MODEL_DISCOVERY_BYTES,
            maximum_depth=32,
            maximum_nodes=10_000,
        )
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            return []
        models: set[str] = set()
        for item in data["data"]:
            if not isinstance(item, dict):
                continue
            model = item.get("id") or item.get("model")
            if not isinstance(model, str) or not model or len(model) > MAX_MODEL_ID_CHARS:
                continue
            if model != model.strip() or any(
                ord(char) < 32 or 127 <= ord(char) < 160 for char in model
            ):
                continue
            models.add(model)
            if len(models) >= MAX_DISCOVERED_MODELS:
                break
        return sorted(models)
    except Exception:
        return []


def _print_config_summary(config_data: dict[str, Any]) -> None:
    """Print a human-readable summary of the generated config."""
    j = config_data.get("judge", {})
    print(f"\n  Judge model:  {safe_display_token(j.get('model', '?'))}")
    print(f"  Base URL:     {safe_display_token(j.get('base_url', '?'))}")
    if j.get("api_key_env"):
        print(f"  API key:      from ${safe_display_token(j['api_key_env'])}")
    elif j.get("api_key"):
        print("  API key:      (stored in config)")
    else:
        print("  API key:      none (free/local)")
    print(f"  Ollama mode:  {j.get('ollama_mode', False)}")
    print(f"  Profile:      {safe_display_token(config_data.get('profile', 'standard'))}")


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
