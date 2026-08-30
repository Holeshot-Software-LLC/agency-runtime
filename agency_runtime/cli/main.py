"""Compatibility facade and entry point for the Agency Runtime CLI.

Command implementations live in cohesive sibling modules.  The facade keeps the
historical import surface stable and constructs dependency bundles at invocation
time so applications and tests can still replace process boundaries safely.
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from collections.abc import Sequence
from typing import Any

from agency_runtime.core.config import load_config
from agency_runtime.core.detect import ProviderDetection, detect_all
from agency_runtime.core.display import safe_display_token
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.provider_validation import validate_provider
from agency_runtime.core.selector.policy import load_policy

from . import _common
from . import config_commands as _config
from . import config_wizard as _wizard
from . import eval_commands as _evals
from . import evidence_commands as _evidence
from . import install_commands as _install
from . import parser as _parser
from . import roster_commands as _roster
from . import service_commands as _services
from . import setup_commands as _setup
from . import workforce_commands as _workforce

_REDACTED = _common.REDACTED
_SECRET_KEY_PARTS = _common.SECRET_KEY_PARTS
_config_display_value = _common.config_display_value
_configure_console_output = _common.configure_console_output
_enforce_local_only_config = _common.enforce_local_only_config
_format_config_value = _common.format_config_value
_is_loopback_url = _common.is_loopback_url
_is_secret_config_part = _common.is_secret_config_part
_nested_config_value = _common.nested_config_value
_print_json = _common.print_json
_store = _common.store


_MAX_MODEL_DISCOVERY_BYTES = _wizard.MAX_MODEL_DISCOVERY_BYTES
_MAX_DISCOVERED_MODELS = _wizard.MAX_DISCOVERED_MODELS
_MAX_MODEL_ID_CHARS = _wizard.MAX_MODEL_ID_CHARS


def _wizard_dependencies(
    *,
    include_model_fetcher: bool = True,
) -> _wizard.WizardDependencies:
    """Capture the facade's current patchable wizard dependencies."""
    return _wizard.WizardDependencies(
        detect=detect_all,
        secret_prompt=getpass.getpass,
        open_url=open_no_redirect,
        provider_validator=validate_provider,
        model_fetcher=_fetch_models_custom if include_model_fetcher else None,
    )


def _detect_for_profile(profile: str):
    return _wizard._detect_for_profile(
        profile,
        dependencies=_wizard_dependencies(),
    )


def _interactive_wizard(detection, profile: str) -> dict[str, Any]:
    return _wizard._interactive_wizard(
        detection,
        profile,
        dependencies=_wizard_dependencies(),
    )


def _guided_provider_chain(detection, profile: str) -> list[dict[str, Any]]:
    return _wizard._guided_provider_chain(
        detection,
        profile,
        dependencies=_wizard_dependencies(),
    )


def _new_provider_entry(detection, profile: str) -> dict[str, Any] | None:
    return _wizard._new_provider_entry(
        detection,
        profile,
        dependencies=_wizard_dependencies(),
    )


def _validate_interactive_provider_chain(
    providers: list[dict[str, Any]],
) -> bool:
    return _wizard._validate_interactive_provider_chain(
        providers,
        dependencies=_wizard_dependencies(),
    )


def _pick_openai_model(provider: ProviderDetection) -> dict[str, Any]:
    return _wizard._pick_openai_model(
        provider,
        dependencies=_wizard_dependencies(),
    )


def _pick_anthropic_model() -> dict[str, Any]:
    return _wizard._pick_anthropic_model(dependencies=_wizard_dependencies())


def _pick_litellm_model(provider: ProviderDetection) -> dict[str, Any]:
    return _wizard._pick_litellm_model(
        provider,
        dependencies=_wizard_dependencies(),
    )


def _prompt_provider_auth(
    *,
    default_env: str,
    base_url: str,
) -> tuple[dict[str, str], str]:
    return _wizard._prompt_provider_auth(
        default_env=default_env,
        base_url=base_url,
        dependencies=_wizard_dependencies(),
    )


def _pick_custom_endpoint() -> dict[str, Any]:
    return _wizard._pick_custom_endpoint(dependencies=_wizard_dependencies())


def _fetch_models_custom(
    base_url: str,
    api_key: str | None = None,
) -> list[str]:
    return _wizard._fetch_models_custom(
        base_url,
        api_key,
        dependencies=_wizard_dependencies(include_model_fetcher=False),
    )


_prompt_install_profile = _wizard._prompt_install_profile
_legacy_judge_from_chain = _wizard._legacy_judge_from_chain
_provider_entry = _wizard._provider_entry
_pick_ollama_model = _wizard._pick_ollama_model
_print_config_summary = _wizard._print_config_summary
_prompt_choice = _wizard._prompt_choice


_seed_starter_roster = _install._seed_starter_roster
_print_install_result = _install._print_install_result
_resolve_control_agents = _install._resolve_control_agents


def _install_dependencies() -> _install.InstallDependencies:
    """Capture the facade's current patchable installation dependencies."""
    return _install.InstallDependencies(
        load_config=load_config,
        store_factory=_store,
        emit_json=_print_json,
        readiness_probe=lambda: _wait_dashboard_ready(),
    )


def cmd_install(args: argparse.Namespace) -> int:
    return _install.cmd_install(args, dependencies=_install_dependencies())


def cmd_uninstall(args: argparse.Namespace) -> int:
    from .uninstall_commands import cmd_uninstall as command

    return command(args)


def _cmd_host_control(args: argparse.Namespace, *, enabled: bool) -> int:
    return _install._cmd_host_control(
        args,
        enabled=enabled,
        dependencies=_install_dependencies(),
    )


def cmd_on(args: argparse.Namespace) -> int:
    return _install.cmd_on(args, dependencies=_install_dependencies())


def cmd_off(args: argparse.Namespace) -> int:
    return _install.cmd_off(args, dependencies=_install_dependencies())


def cmd_status(args: argparse.Namespace) -> int:
    return _install.cmd_status(args, dependencies=_install_dependencies())


def cmd_host_canary(args: argparse.Namespace) -> int:
    return _install.cmd_host_canary(args, dependencies=_install_dependencies())


def cmd_battery(args: argparse.Namespace) -> int:
    from agency_runtime.core.harness_battery import run_battery_cli

    return run_battery_cli(args)


def _configuration_dependencies() -> _config.ConfigurationDependencies:
    """Capture the facade's current patchable configuration dependencies."""
    return _config.ConfigurationDependencies(
        load_config=load_config,
        store_factory=_store,
        seed_starter_roster=_seed_starter_roster,
        detect_for_profile=_detect_for_profile,
        interactive_wizard=_interactive_wizard,
        validate_chain=_validate_interactive_provider_chain,
        secret_prompt=getpass.getpass,
        configure_console=_configure_console_output,
    )


def cmd_configure(args: argparse.Namespace) -> int:
    return _config.cmd_configure(
        args,
        dependencies=_configuration_dependencies(),
    )


def cmd_doctor(args: argparse.Namespace) -> int:
    return _config.cmd_doctor(args, dependencies=_configuration_dependencies())


def cmd_config_show(args: argparse.Namespace) -> int:
    return _config.cmd_config_show(args, dependencies=_configuration_dependencies())


def cmd_config_path(args: argparse.Namespace) -> int:
    return _config.cmd_config_path(args)


def cmd_config_get(args: argparse.Namespace) -> int:
    return _config.cmd_config_get(args, dependencies=_configuration_dependencies())


def cmd_config_set(args: argparse.Namespace) -> int:
    return _config.cmd_config_set(args, dependencies=_configuration_dependencies())


def cmd_config_provider_list(args: argparse.Namespace) -> int:
    return _config.cmd_config_provider_list(args)


def cmd_config_provider_models(args: argparse.Namespace) -> int:
    return _config.cmd_config_provider_models(args)


def cmd_config_provider_set(args: argparse.Namespace) -> int:
    return _config.cmd_config_provider_set(args)


def cmd_config_provider_remove(args: argparse.Namespace) -> int:
    return _config.cmd_config_provider_remove(args)


def cmd_config_validate(args: argparse.Namespace) -> int:
    return _config.cmd_config_validate(
        args,
        dependencies=_configuration_dependencies(),
    )


def cmd_config_reset(args: argparse.Namespace) -> int:
    return _config.cmd_config_reset(
        args,
        dependencies=_configuration_dependencies(),
    )


cmd_sync = _roster.cmd_sync
cmd_source_add = _roster.cmd_source_add
cmd_source_list = _roster.cmd_source_list
cmd_roster_list = _roster.cmd_roster_list
cmd_roster_diff = _roster.cmd_roster_diff
cmd_roster_approve = _roster.cmd_roster_approve
cmd_roster_activate = _roster.cmd_roster_activate
cmd_roster_scans = _roster.cmd_roster_scans
cmd_roster_remediation_queue = _roster.cmd_roster_remediation_queue
cmd_roster_retire = _roster.cmd_roster_retire
cmd_roster_rollback = _roster.cmd_roster_rollback
cmd_roster_upstream_status = _roster.cmd_roster_upstream_status
cmd_roster_upstream_import = _roster.cmd_roster_upstream_import
cmd_roster_candidate_audit = _roster.cmd_roster_candidate_audit
cmd_roster_candidate_findings = _roster.cmd_roster_candidate_findings
cmd_roster_candidate_reject = _roster.cmd_roster_candidate_reject
cmd_roster_candidate_compare = _roster.cmd_roster_candidate_compare
cmd_agents_list = _roster.cmd_agents_list
cmd_agent_enable = _roster.cmd_agent_enable
cmd_agent_disable = _roster.cmd_agent_disable
_search = _roster._search
cmd_search = _roster.cmd_search
cmd_route = _roster.cmd_route
cmd_explain = _roster.cmd_explain
cmd_eval_host_parity = _roster.cmd_eval_host_parity
cmd_eval_spawn_authority = _roster.cmd_eval_spawn_authority
cmd_eval_staffing = _roster.cmd_eval_staffing
cmd_eval_routing = _roster.cmd_eval_routing
cmd_eval_compare = _evals.cmd_eval_compare
cmd_eval_decision_conformance = _evals.cmd_eval_decision_conformance
cmd_eval_full_roster = _evals.cmd_eval_full_roster
cmd_eval_shadow_recall = _evals.cmd_eval_shadow_recall
cmd_eval_product = _evals.cmd_eval_product
cmd_eval_upstream_architecture = _evals.cmd_eval_upstream_architecture
cmd_eval_upstream_selection = _evals.cmd_eval_upstream_selection
cmd_eval_workforce = _evals.cmd_eval_workforce
cmd_smoke = _roster.cmd_smoke
cmd_db_stats = _roster.cmd_db_stats
cmd_db_trim = _roster.cmd_db_trim


def cmd_setup(args: argparse.Namespace) -> int:
    """Run setup through facade callbacks so historical monkeypatching remains valid."""

    return _setup.cmd_setup(
        args,
        dependencies=_setup.SetupDependencies(
            configure=cmd_configure,
            validate=cmd_config_validate,
            install=cmd_install,
            dashboard_service=cmd_dashboard_service,
            doctor=cmd_doctor,
            smoke=cmd_smoke,
        ),
    )


def _workforce_dependencies() -> _workforce.WorkforceDependencies:
    return _workforce.WorkforceDependencies(store_factory=_store, emit_json=_print_json)


def cmd_workforce_list(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_list(args, dependencies=_workforce_dependencies())


def cmd_workforce_search(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_search(args, dependencies=_workforce_dependencies())


def cmd_workforce_duplicates(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_duplicates(args, dependencies=_workforce_dependencies())


def cmd_workforce_consolidate(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_consolidate(args, dependencies=_workforce_dependencies())


def cmd_workforce_show(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_show(args, dependencies=_workforce_dependencies())


def cmd_workforce_prompt(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_prompt(args, dependencies=_workforce_dependencies())


def cmd_workforce_transition(args: argparse.Namespace) -> int:
    return _workforce.cmd_workforce_transition(args, dependencies=_workforce_dependencies())


def cmd_contractor_list(args: argparse.Namespace) -> int:
    return _workforce.cmd_contractor_list(args, dependencies=_workforce_dependencies())


def cmd_hiring_list(args: argparse.Namespace) -> int:
    return _workforce.cmd_hiring_list(args, dependencies=_workforce_dependencies())


def cmd_hiring_show(args: argparse.Namespace) -> int:
    return _workforce.cmd_hiring_show(args, dependencies=_workforce_dependencies())


def cmd_hiring_approve(args: argparse.Namespace) -> int:
    return _workforce.cmd_hiring_approve(args, dependencies=_workforce_dependencies())


def cmd_policy(args: argparse.Namespace) -> int:
    dependencies = _roster.RosterDependencies(
        store_factory=_store,
        emit_json=_print_json,
        policy_loader=load_policy,
    )
    return _roster.cmd_policy(args, dependencies=dependencies)


cmd_evidence_children = _evidence.cmd_evidence_children
cmd_evidence_child_launches = _evidence.cmd_evidence_child_launches
cmd_evidence_latency = _evidence.cmd_evidence_latency
cmd_evidence_intent = _evidence.cmd_evidence_intent
cmd_evidence_rejections = _evidence.cmd_evidence_rejections
cmd_evidence_selections = _evidence.cmd_evidence_selections
cmd_evidence_wiring = _evidence.cmd_evidence_wiring

cmd_serve = _services.cmd_serve
cmd_mcp = _services.cmd_mcp
cmd_hook = _services.cmd_hook
cmd_dashboard = _services.cmd_dashboard
_wait_dashboard_ready = _services._wait_dashboard_ready
cmd_dashboard_service = _services.cmd_dashboard_service


def cmd_version(args: argparse.Namespace) -> int:
    from .upgrade_commands import cmd_version as command

    return command(args)


def cmd_upgrade(args: argparse.Namespace) -> int:
    from .upgrade_commands import cmd_upgrade as command

    return command(args)


_positive_int = _parser._positive_int

_COMMAND_NAMES = (
    "cmd_agent_disable",
    "cmd_agent_enable",
    "cmd_agents_list",
    "cmd_config_get",
    "cmd_config_path",
    "cmd_config_provider_list",
    "cmd_config_provider_models",
    "cmd_config_provider_remove",
    "cmd_config_provider_set",
    "cmd_config_reset",
    "cmd_config_set",
    "cmd_config_show",
    "cmd_config_validate",
    "cmd_configure",
    "cmd_contractor_list",
    "cmd_dashboard",
    "cmd_dashboard_service",
    "cmd_db_stats",
    "cmd_db_trim",
    "cmd_doctor",
    "cmd_eval_compare",
    "cmd_eval_decision_conformance",
    "cmd_eval_full_roster",
    "cmd_eval_shadow_recall",
    "cmd_eval_product",
    "cmd_eval_upstream_architecture",
    "cmd_eval_upstream_selection",
    "cmd_eval_host_parity",
    "cmd_eval_spawn_authority",
    "cmd_eval_staffing",
    "cmd_eval_routing",
    "cmd_eval_workforce",
    "cmd_evidence_child_launches",
    "cmd_evidence_children",
    "cmd_evidence_intent",
    "cmd_evidence_latency",
    "cmd_evidence_rejections",
    "cmd_evidence_selections",
    "cmd_evidence_wiring",
    "cmd_explain",
    "cmd_hook",
    "cmd_hiring_approve",
    "cmd_hiring_list",
    "cmd_hiring_show",
    "cmd_host_canary",
    "cmd_battery",
    "cmd_install",
    "cmd_uninstall",
    "cmd_mcp",
    "cmd_off",
    "cmd_on",
    "cmd_policy",
    "cmd_roster_activate",
    "cmd_roster_approve",
    "cmd_roster_diff",
    "cmd_roster_list",
    "cmd_roster_remediation_queue",
    "cmd_roster_retire",
    "cmd_roster_rollback",
    "cmd_roster_scans",
    "cmd_roster_upstream_status",
    "cmd_roster_upstream_import",
    "cmd_roster_candidate_audit",
    "cmd_roster_candidate_findings",
    "cmd_roster_candidate_reject",
    "cmd_roster_candidate_compare",
    "cmd_route",
    "cmd_search",
    "cmd_serve",
    "cmd_smoke",
    "cmd_setup",
    "cmd_source_add",
    "cmd_source_list",
    "cmd_status",
    "cmd_sync",
    "cmd_upgrade",
    "cmd_version",
    "cmd_workforce_list",
    "cmd_workforce_prompt",
    "cmd_workforce_consolidate",
    "cmd_workforce_duplicates",
    "cmd_workforce_search",
    "cmd_workforce_show",
    "cmd_workforce_transition",
)


def build_parser() -> argparse.ArgumentParser:
    """Build the parser against facade callbacks to preserve monkeypatching."""
    handlers = {name: globals()[name] for name in _COMMAND_NAMES}
    return _parser.build_parser(handlers)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and translate expected command errors into exit status 1."""
    _configure_console_output()
    parser = build_parser()
    args = parser.parse_args(argv)
    _print_cached_update_notice(args)
    try:
        return int(args.func(args))
    except (KeyError, OSError, ValueError, RuntimeError) as exc:
        print(f"agency: error: {safe_display_token(str(exc), limit=500)}", file=sys.stderr)
        return 1


def _print_cached_update_notice(args: argparse.Namespace) -> None:
    """Notify interactive human commands from cache without network or Git work."""

    if not sys.stderr.isatty() or bool(getattr(args, "json", False)):
        return
    command = getattr(args, "command", "")
    if not isinstance(command, str) or command in {
        "codex",
        "dashboard",
        "hook",
        "mcp",
        "run",
        "serve",
        "upgrade",
        "version",
    }:
        return
    setting = os.environ.get("AGENCY_UPDATE_NOTICES", "1").strip().casefold()
    if setting in {"0", "false", "no", "off"}:
        return
    try:
        from agency_runtime.core.update_service import cached_startup_notice

        notice = cached_startup_notice()
    except (OSError, PermissionError, RuntimeError, TypeError, ValueError):
        return
    if notice:
        print(notice, file=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
