"""Configuration document commands and guided setup orchestration."""

from __future__ import annotations

import argparse
import getpass
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded
from agency_runtime.core.cli_transport import discover_cli_models
from agency_runtime.core.config import (
    AgencyConfig,
    config_to_yaml,
    load_config,
    reset_config_cache,
)
from agency_runtime.core.configuration import (
    apply_config_operations,
    is_text_set_path,
    read_config_revision,
    read_config_state,
    replace_config_document,
    resolve_config_path,
)
from agency_runtime.core.configuration_contracts import MAX_CONFIG_BYTES
from agency_runtime.core.detect import generate_config_from_detection
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.doctor import format_report_human, run_doctor

from ._common import (
    config_display_value as _config_display_value,
)
from ._common import (
    configure_console_output as _configure_console_output,
)
from ._common import (
    enforce_local_only_config as _enforce_local_only_config,
)
from ._common import (
    format_config_value as _format_config_value,
)
from ._common import (
    is_secret_config_part as _is_secret_config_part,
)
from ._common import (
    nested_config_value as _nested_config_value,
)
from ._common import (
    print_json as _print_json,
)
from ._common import (
    store,
)
from .config_wizard import (
    _detect_for_profile,
    _interactive_wizard,
    _prompt_install_profile,
    _validate_interactive_provider_chain,
)
from .install_commands import _seed_starter_roster

_MAX_SECRET_CHARS = 4096


def _read_stdin_bounded(*, limit: int, line: bool = False) -> str:
    """Read a CLI value without allowing an input stream to exhaust memory."""
    raw = sys.stdin.readline(limit + 2) if line else sys.stdin.read(limit + 1)
    value = raw.rstrip("\r\n") if line else raw
    if len(value) > limit or (line and len(raw) > limit + 1):
        raise ValueError("config value from standard input exceeds the size limit")
    return value


@dataclass(frozen=True, slots=True)
class ConfigurationDependencies:
    """Patchable filesystem, prompt, and wizard boundaries."""

    load_config: Callable[..., AgencyConfig] = load_config
    store_factory: Callable[[AgencyConfig | None], Any] = store
    seed_starter_roster: Callable[[Any], int] = _seed_starter_roster
    detect_for_profile: Callable[[str], Any] = _detect_for_profile
    interactive_wizard: Callable[[Any, str], dict[str, Any]] = _interactive_wizard
    validate_chain: Callable[[list[dict[str, Any]]], bool] = _validate_interactive_provider_chain
    secret_prompt: Callable[[str], str] = getpass.getpass
    configure_console: Callable[[], None] = _configure_console_output


DEFAULT_DEPENDENCIES = ConfigurationDependencies()


def cmd_configure(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Guided setup wizard or non-interactive config generation."""
    dependencies.configure_console()

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
    detection = dependencies.detect_for_profile(profile)
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
    print(f"  {'✅' if p.litellm_available else '❌'} LiteLLM proxy: {p.litellm_base_url}")
    print()
    print(f"  {'✅' if a.hermes else '❌'} Hermes adapter")
    print(f"  {'✅' if a.openclaw else '❌'} OpenClaw adapter")
    print(f"  {'✅' if a.codex else '❌'} Codex CLI")
    print(f"  {'✅' if a.claude else '❌'} Claude Code CLI")
    print()

    if args.non_interactive:
        config_data = generate_config_from_detection(detection, profile=profile)
    else:
        config_data = dependencies.interactive_wizard(detection, profile)
    config_data = _enforce_local_only_config(config_data)

    if not args.non_interactive and not dependencies.validate_chain(
        config_data.get("providers", [])
    ):
        print("\n❌ Provider validation failed; configuration was not written.")
        return 1

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

    # Install starter roster
    reset_config_cache()
    cfg = dependencies.load_config(reload=True)
    try:
        runtime_store = dependencies.store_factory(cfg)
        count = dependencies.seed_starter_roster(runtime_store)
    except OSError as exc:
        print(f"\n⚠️  Config written to {config_path}")
        print(
            "❌ Starter roster and SQLite initialization did not complete: "
            f"{safe_display_token(str(exc), limit=500)}"
        )
        print("   Run `agency install` from a normal user shell to complete setup.")
        return 1

    print(f"\n✅ Config written to {config_path}")
    print(f"✅ Starter roster installed: {count} agents")
    print(
        "✅ Governed contractors: "
        f"{int(getattr(count, 'contractors_installed', 0))} installed, "
        f"{int(getattr(count, 'contractors_upgraded', 0))} upgraded, "
        f"{int(getattr(count, 'contractors_existing', 0))} already current, "
        f"{int(getattr(count, 'contractors_preserved', 0))} preserved"
    )
    print(f"✅ SQLite database initialized: {cfg.store.resolved_path()}")
    print("\nNext steps:")
    print("  agency doctor              — verify everything is working")
    print('  agency search "code review" — test the selector')
    print('  agency route "review this PR" — see routing in action')
    return 0


def cmd_doctor(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    cfg = dependencies.load_config()
    report = run_doctor(cfg, fix_perms=bool(getattr(args, "fix_perms", False)))
    if args.json:
        _print_json(report.to_dict())
    else:
        print(format_report_human(report))
    return report.exit_code


# ── Config subcommands ───────────────────────────────────────


def cmd_config_show(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    cfg = dependencies.load_config()
    print(config_to_yaml(cfg, redact=not args.raw))
    return 0


def cmd_config_path(args: argparse.Namespace) -> int:
    path = resolve_config_path()
    suffix = "" if path.exists() else " (not created; using bundled defaults)"
    print(f"{path}{suffix}")
    return 0


def cmd_config_get(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    cfg = dependencies.load_config()
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


def _config_set_input_modes(args: argparse.Namespace) -> int:
    """Count explicitly selected non-positional value sources."""
    return sum(bool(getattr(args, name, False)) for name in ("stdin", "prompt", "clear"))


def _clear_secret_operation(
    args: argparse.Namespace,
    *,
    is_secret: bool,
) -> dict[str, Any]:
    """Build a validated secret-clear operation."""
    if not is_secret or args.value is not None:
        raise ValueError("--clear is valid only for a secret key without a value")
    return {"op": "secret", "path": args.key, "action": "clear"}


def _replace_secret_operation(
    args: argparse.Namespace,
    dependencies: ConfigurationDependencies,
) -> dict[str, Any]:
    """Read a secret through an approved input channel and build its operation."""
    if args.value is not None:
        raise ValueError("secret values are not accepted as arguments; use --stdin or --prompt")
    if getattr(args, "stdin", False):
        value = _read_stdin_bounded(limit=_MAX_SECRET_CHARS, line=True)
    elif getattr(args, "prompt", False):
        value = dependencies.secret_prompt(f"New value for {args.key}: ")
    else:
        raise ValueError("secret updates require --stdin, --prompt, or --clear")
    return {
        "op": "secret",
        "path": args.key,
        "action": "replace",
        "value": value,
    }


def _normalize_config_set_value(key: str, value: Any) -> Any:
    """Retain the adapter tri-state string contract for YAML booleans."""
    if key.startswith("adapters.") and key.endswith(".enabled") and isinstance(value, bool):
        return "true" if value else "false"
    return value


def _literal_stdin_text(raw_value: str) -> str:
    """Keep piped text as written, minus the one newline that ends a text stream.

    YAML folds a multi-line plain scalar into one line, which is how a five-line
    operator policy came back as one (AR-359). A text-valued key never needs YAML
    to be typed, so its ``--stdin`` bytes are the value: internal line breaks
    survive, and only the single trailing newline that ``echo`` or a heredoc
    appends is dropped. The key's own validator still applies its normalization.
    """
    if raw_value.endswith("\r\n"):
        return raw_value[:-2]
    return raw_value.removesuffix("\n")


def _parse_config_set_yaml(raw_value: str) -> Any:
    """Load one bounded YAML value, reporting any parse failure as a CLI error."""
    try:
        return safe_load_bounded(raw_value)
    except (BoundedYAMLError, yaml.YAMLError) as exc:
        raise ValueError("config value is not valid YAML") from exc


def _plain_config_set_operation(args: argparse.Namespace) -> dict[str, Any]:
    """Parse a bounded non-secret value and build its set operation."""
    if getattr(args, "prompt", False):
        raise ValueError("--prompt and --clear are valid only for secret keys")
    from_stdin = bool(getattr(args, "stdin", False))
    if from_stdin and args.value is not None:
        raise ValueError("provide either a positional value or --stdin, not both")
    raw_value = _read_stdin_bounded(limit=MAX_CONFIG_BYTES) if from_stdin else args.value
    if raw_value is None:
        raise ValueError("config set requires a value or --stdin")
    if from_stdin and is_text_set_path(args.key):
        parsed_value: Any = _literal_stdin_text(raw_value)
    else:
        parsed_value = _parse_config_set_yaml(raw_value)
    return {
        "op": "set",
        "path": args.key,
        "value": _normalize_config_set_value(args.key, parsed_value),
    }


def _config_set_operation(
    args: argparse.Namespace,
    *,
    is_secret: bool,
    dependencies: ConfigurationDependencies,
) -> dict[str, Any]:
    """Select and validate the requested configuration mutation."""
    if _config_set_input_modes(args) > 1:
        raise ValueError("--stdin, --prompt, and --clear are mutually exclusive")
    if getattr(args, "clear", False):
        return _clear_secret_operation(args, is_secret=is_secret)
    if is_secret:
        return _replace_secret_operation(args, dependencies)
    return _plain_config_set_operation(args)


def _config_set_notes(key: str, result: Any) -> list[str]:
    """Describe policy, environment, and restart effects of a config write."""
    notes: list[str] = []
    if result.policy_enforced:
        notes.append("local-only policy enforced")
    if key in result.state.environment_overrides:
        notes.append(f"effective value is overridden by {result.state.environment_overrides[key]}")
    if result.restart_required:
        notes.append(f"restart required: {', '.join(result.restart_required)}")
    return notes


def cmd_config_set(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    parts = args.key.split(".")
    if not all(parts):
        raise ValueError("config key must be a non-empty dotted path")
    is_secret = _is_secret_config_part(parts[-1])
    operation = _config_set_operation(
        args,
        is_secret=is_secret,
        dependencies=dependencies,
    )

    state = read_config_state()
    result = apply_config_operations(
        [operation],
        expected_revision=state.revision,
    )
    effective_value = _nested_config_value(result.state.effective, parts)
    display = _config_display_value(effective_value, path=tuple(parts), raw=False)
    notes = _config_set_notes(args.key, result)
    suffix = f" ({'; '.join(notes)})" if notes else ""
    print(f"Set {args.key} = {_format_config_value(display)}{suffix}")
    return 0


def _editable_providers(state: Any) -> list[dict[str, Any]]:
    raw = state.persisted.get("providers", [])
    if not isinstance(raw, list):
        return []
    return [
        {str(key): value for key, value in provider.items() if str(key) != "api_key"}
        for provider in raw
        if isinstance(provider, dict)
    ]


def cmd_config_provider_list(args: argparse.Namespace) -> int:
    """Show the ordered provider chain without exposing direct secrets."""

    providers = _editable_providers(read_config_state())
    if args.json:
        _print_json({"providers": providers})
        return 0
    if not providers:
        print("No inference providers configured.")
        return 0
    for index, provider in enumerate(providers, start=1):
        model = str(provider.get("model") or "default")
        endpoint = str(provider.get("transport") or provider.get("base_url") or "not set")
        effort = str(provider.get("reasoning_effort") or "default")
        print(
            f"{index}. {provider.get('name')} · {provider.get('type')} · "
            f"model/router={model} · reasoning={effort} · {endpoint}"
        )
    return 0


def cmd_config_provider_models(args: argparse.Namespace) -> int:
    """List account-visible models for one authenticated CLI transport."""

    catalog = discover_cli_models(
        args.transport,
        refresh=bool(args.refresh),
        timeout=float(args.timeout),
    )
    payload = catalog.as_dict()
    if args.json:
        _print_json(payload)
    else:
        if catalog.models:
            for model in catalog.models:
                detail = f" - {model.description}" if model.description else ""
                efforts = ", ".join(model.supported_reasoning_levels)
                reasoning = (
                    f" · reasoning={efforts} (default {model.default_reasoning_level})"
                    if efforts
                    else ""
                )
                print(f"{model.slug} · {model.display_name}{reasoning}{detail}")
            print(f"Source: {catalog.source} · observed {catalog.observed_at}")
        else:
            print(catalog.error or "No visible models were reported.")
    return 0 if catalog.models else 1


def cmd_config_provider_set(args: argparse.Namespace) -> int:
    """Add or update one named inference provider while preserving its secret."""

    state = read_config_state()
    providers = _editable_providers(state)
    target_name = str(args.name).strip()
    index = next(
        (
            position
            for position, provider in enumerate(providers)
            if str(provider.get("name") or "").casefold() == target_name.casefold()
        ),
        None,
    )
    existing = providers[index] if index is not None else {}
    provider_type = str(args.type or existing.get("type") or "").strip().casefold()
    if not provider_type:
        raise ValueError("--type is required when adding a provider")
    existing_type = str(existing.get("type") or "").strip().casefold()
    provider_type_changed = bool(args.type is not None and provider_type != existing_type)
    cli_provider = provider_type == "cli"
    transport = (
        str(args.transport if args.transport is not None else existing.get("transport") or "")
        .strip()
        .casefold()
        if cli_provider
        else ""
    )
    requested_effort = getattr(args, "reasoning_effort", None)
    if requested_effort is None:
        reasoning_effort = str(existing.get("reasoning_effort") or "").strip().casefold()
    else:
        reasoning_effort = "" if requested_effort == "default" else str(requested_effort)
    if transport != "codex":
        if requested_effort not in (None, "default"):
            raise ValueError("--reasoning-effort is supported only for Codex CLI providers")
        reasoning_effort = ""
    updated = {
        "name": target_name,
        "type": provider_type,
        "transport": transport,
        "model": str(args.model if args.model is not None else existing.get("model") or "").strip(),
        "base_url": ""
        if cli_provider
        else str(
            args.base_url if args.base_url is not None else existing.get("base_url") or ""
        ).strip(),
        "api_key_env": ""
        if cli_provider
        else str(
            args.api_key_env if args.api_key_env is not None else existing.get("api_key_env") or ""
        ).strip(),
        "ollama_mode": provider_type == "ollama"
        or (not provider_type_changed and bool(existing.get("ollama_mode", False))),
        "timeout": (
            float(args.timeout)
            if args.timeout is not None
            else float(existing.get("timeout", 15.0))
        ),
        "reasoning_effort": reasoning_effort,
    }
    if index is None:
        providers.append(updated)
        index = len(providers) - 1
    else:
        providers[index] = updated
    operations: list[dict[str, Any]] = [{"op": "set", "path": "providers", "value": providers}]
    if cli_provider:
        operations.append(
            {
                "op": "secret",
                "path": f"providers.{index}.api_key",
                "action": "clear",
            }
        )
    result = apply_config_operations(
        operations,
        expected_revision=state.revision,
    )
    notes = _config_set_notes("providers", result)
    suffix = f" ({'; '.join(notes)})" if notes else ""
    print(
        f"Set provider {target_name} at position {index + 1}: "
        f"type={provider_type}, model/router={updated['model'] or 'default'}, "
        f"reasoning={updated['reasoning_effort'] or 'default'}{suffix}"
    )
    return 0


def cmd_config_provider_remove(args: argparse.Namespace) -> int:
    """Remove one named provider from the ordered chain."""

    state = read_config_state()
    providers = _editable_providers(state)
    target = str(args.name).strip().casefold()
    retained = [
        provider for provider in providers if str(provider.get("name") or "").casefold() != target
    ]
    if len(retained) == len(providers):
        raise ValueError(f"provider not found: {args.name}")
    apply_config_operations(
        [{"op": "set", "path": "providers", "value": retained}],
        expected_revision=state.revision,
    )
    print(f"Removed provider {args.name}")
    return 0


def cmd_config_validate(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Validate config by running doctor checks."""
    cfg = dependencies.load_config()
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


def cmd_config_reset(
    args: argparse.Namespace,
    *,
    dependencies: ConfigurationDependencies = DEFAULT_DEPENDENCIES,
) -> int:
    """Reset config to defaults."""
    cfg = dependencies.load_config()
    config_path = (
        Path(cfg.config_path)
        if cfg.config_path
        else Path.home() / ".agency-runtime" / "agency.yaml"
    )
    if config_path.exists():
        resp = input(f"Delete {config_path} and reset to defaults? [y/N] ").strip().lower()
        if resp != "y":
            print("Aborted.")
            return 0
        config_path.unlink()
    print("Config reset. Run `agency configure` to set up again.")
    return 0
