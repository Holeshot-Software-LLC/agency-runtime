"""Declarative argparse construction independent of command implementations."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping

from agency_runtime import __version__
from agency_runtime.core.child_delivery_evidence import MAX_CHILD_DETAIL_RESULTS
from agency_runtime.core.child_launch_outcomes import MAX_CHILD_LAUNCHES
from agency_runtime.core.evals.product_scenarios import PRODUCT_SCENARIOS_BY_ID
from agency_runtime.core.evals.upstream_selection import CASES as UPSTREAM_SELECTION_CASES
from agency_runtime.core.evals.workforce_selection import CASES
from agency_runtime.core.harness_battery import BATTERY_DEFAULT_TRIALS, BATTERY_MAX_TRIALS
from agency_runtime.core.host_capabilities import EXECUTION_HOSTS
from agency_runtime.core.installer_contracts import HOSTS
from agency_runtime.core.policy.profiles import PROFILES
from agency_runtime.core.rule8_evidence import MAX_RULE8_EVIDENCE_ROWS
from agency_runtime.core.runtime_control_command import parse_runtime_control_command

CommandHandler = Callable[[argparse.Namespace], int]
Handlers = Mapping[str, CommandHandler]
Subparsers = argparse._SubParsersAction

_NATIVE_HOOK_EVENTS = (
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PermissionRequest",
    "PostToolUse",
    "PostToolUseFailure",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "PostCompact",
    "Stop",
    "SessionEnd",
)


class _VerifyCodexActivationAction(argparse.Action):
    """Bind the exact verification-only mode at parse time."""

    def __init__(self, option_strings, dest, **kwargs):
        super().__init__(option_strings, dest, nargs=0, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None) -> None:
        del parser, values, option_string
        setattr(namespace, self.dest, True)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _update_timeout(value: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be from 0.1 through 30 seconds") from exc
    if not 0.1 <= parsed <= 30:
        raise argparse.ArgumentTypeError("must be from 0.1 through 30 seconds")
    return parsed


def _search_limit(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 100:
        raise argparse.ArgumentTypeError("must be an integer from 1 through 100")
    return parsed


def _battery_trials(value: str) -> int:
    """Per-probe trial count for ``agency battery`` (AR-360); k stays small
    because every trial is a real host turn with real model spend."""

    parsed = _positive_int(value)
    if parsed > BATTERY_MAX_TRIALS:
        raise argparse.ArgumentTypeError(f"must be an integer from 1 through {BATTERY_MAX_TRIALS}")
    return parsed


def _bind(
    parser: argparse.ArgumentParser,
    handlers: Handlers,
    name: str,
) -> None:
    parser.set_defaults(func=handlers[name])


def _runtime_control_action(action: str) -> str:
    """Resolve CLI control names through the canonical exact parser."""

    command = parse_runtime_control_command(f"agency {action}")
    if command is None:  # pragma: no cover - static registration invariant
        raise RuntimeError("CLI runtime control registration is invalid")
    return command.action


def _add_update_target_arguments(
    parser: argparse.ArgumentParser,
    *,
    timeout_default: float | None,
) -> None:
    target = parser.add_mutually_exclusive_group()
    target.add_argument(
        "--channel",
        choices=["release", "main"],
        default=None,
        help="Resolve the latest stable release or the current main commit (default: release)",
    )
    target.add_argument(
        "--version",
        dest="target_version",
        default=None,
        help="Resolve one canonical release version such as 0.2.0 or 0.2.0rc1",
    )
    target.add_argument(
        "--ref",
        dest="target_ref",
        default=None,
        help="Resolve one bounded Git tag, branch, or full commit ref",
    )
    cache_mode = parser.add_mutually_exclusive_group()
    cache_mode.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore a fresh cached result and query GitHub again",
    )
    cache_mode.add_argument(
        "--cached",
        action="store_true",
        help="Read only the local update cache without network or GitHub CLI access",
    )
    parser.add_argument(
        "--timeout",
        type=_update_timeout,
        default=timeout_default,
        help="Maximum GitHub update-check time in seconds (0.1 through 30)",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable results")


def _register_updates(sub: Subparsers, handlers: Handlers) -> None:
    version = sub.add_parser(
        "version",
        help="Show installed package, source commit, and optional update identity",
    )
    version.add_argument(
        "--check",
        action="store_true",
        help="Compare the installed identity with the selected remote target",
    )
    _add_update_target_arguments(version, timeout_default=None)
    _bind(version, handlers, "cmd_version")

    upgrade = sub.add_parser(
        "upgrade",
        help="Resolve an immutable target and print an attended upgrade plan",
    )
    upgrade.add_argument(
        "upgrade_action",
        nargs="?",
        choices=["check", "plan"],
        default="plan",
        help="Use 'check' to inspect availability without printing install commands",
    )
    _add_update_target_arguments(upgrade, timeout_default=5.0)
    _bind(upgrade, handlers, "cmd_upgrade")


def _register_install(sub: Subparsers, handlers: Handlers) -> None:
    install = sub.add_parser(
        "install", help="Install Agency Runtime — seed roster + wire into agent hosts"
    )
    install.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=None,
        help="Verify the already-configured profile; use `agency configure` to change it",
    )
    install.add_argument(
        "--config",
        default=None,
        help="Load and bind this exact Agency YAML configuration for the installation",
    )
    install_target = install.add_mutually_exclusive_group()
    install_target.add_argument(
        "--all",
        action="store_true",
        help="Auto-detect and wire into every AI agent host found",
    )
    install_target.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude", "zcode"],
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
    install_action.add_argument(
        "--verify-activation",
        action=_VerifyCodexActivationAction,
        default=False,
        help=(
            "Verify an already installed Codex adapter in the normal user profile "
            "without reinstalling it or bypassing hook trust"
        ),
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
        "--autonomous",
        action="store_true",
        help=(
            "Use the harness-supported hook-trust bypass for this explicit activation "
            "verification without changing persistent trust state"
        ),
    )
    install.add_argument(
        "--production-container",
        action="store_true",
        help=(
            "Fail-closed dedicated-container install; for Codex, install system-managed "
            "Agency hooks and prove a fresh normal invocation"
        ),
    )
    install.add_argument(
        "--activation-timeout",
        type=float,
        default=180.0,
        help="Maximum current-profile Codex activation check time in seconds",
    )
    install.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        install,
        handlers,
        "cmd_install",
    )


def _plan_digest(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise argparse.ArgumentTypeError("must be one 64-character lowercase plan digest")
    return normalized


def _register_uninstall(sub: Subparsers, handlers: Handlers) -> None:
    uninstall = sub.add_parser(
        "uninstall",
        help="Remove exact owned Agency integrations from selected agent hosts",
    )
    target = uninstall.add_mutually_exclusive_group(required=True)
    target.add_argument(
        "--all",
        action="store_true",
        help="Find every host with Agency integration evidence",
    )
    target.add_argument(
        "--agent",
        choices=list(HOSTS),
        default=None,
        help="Remove Agency from one specific agent host",
    )
    mode = uninstall.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Print a write-free exact plan and confirmation digest",
    )
    mode.add_argument(
        "--confirm-plan",
        type=_plan_digest,
        default=None,
        help="Apply only the exact digest emitted by a preceding dry run",
    )
    uninstall.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        uninstall,
        handlers,
        "cmd_uninstall",
    )


def _register_host_control(sub: Subparsers, handlers: Handlers) -> None:
    on_p = sub.add_parser(
        _runtime_control_action("on"),
        help="Enable Agency Runtime for detected hosts or globally",
    )
    on_target = on_p.add_mutually_exclusive_group()
    on_target.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude", "zcode"],
        default=None,
        help="Host to enable (default: every detected host)",
    )
    on_target.add_argument(
        "--global",
        dest="global_control",
        action="store_true",
        help="Enable Agency Runtime globally across every host",
    )
    on_p.add_argument(
        "--dry-run", action="store_true", help="Print the planned change without applying it"
    )
    on_p.add_argument(
        "--native",
        action="store_true",
        help="Use the host plugin lifecycle instead of immediate soft control",
    )
    on_p.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        on_p,
        handlers,
        "cmd_on",
    )

    off_p = sub.add_parser(
        _runtime_control_action("off"),
        help="Disable Agency Runtime for detected hosts or globally",
    )
    off_target = off_p.add_mutually_exclusive_group()
    off_target.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude", "zcode"],
        default=None,
        help="Host to disable (default: every detected host)",
    )
    off_target.add_argument(
        "--global",
        dest="global_control",
        action="store_true",
        help="Disable Agency Runtime globally across every host",
    )
    off_p.add_argument(
        "--dry-run", action="store_true", help="Print the planned change without applying it"
    )
    off_p.add_argument(
        "--native",
        action="store_true",
        help="Use the host plugin lifecycle instead of immediate soft control",
    )
    off_p.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        off_p,
        handlers,
        "cmd_off",
    )

    status_p = sub.add_parser(
        _runtime_control_action("status"),
        help="Show Agency-wide, native, and per-host runtime control state",
    )
    status_p.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude", "zcode"],
        default=None,
        help="Host to inspect (default: every supported host)",
    )
    status_p.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(status_p, handlers, "cmd_status")

    canary_p = sub.add_parser(
        "host-canary",
        help="Inspect host readiness or run an exact-confirmed live canary",
    )
    canary_p.add_argument(
        "agent", choices=["hermes", "openclaw", "codex", "claude", "zcode"], help="Host to verify"
    )
    canary_p.add_argument(
        "--execute",
        action="store_true",
        help="Run the isolated live invocation after readiness inspection",
    )
    canary_p.add_argument(
        "--accepted-outcome",
        action="store_true",
        help="Use Claude's exact serial producer/verifier accepted-outcome canary",
    )
    canary_p.add_argument(
        "--mode",
        choices=["agency", "native-only"],
        default="agency",
        help="Require Agency evidence or prove a clean native-only bypass",
    )
    canary_p.add_argument(
        "--profile-scope",
        choices=["isolated-profile", "current-profile"],
        default="isolated-profile",
        help="Use a disposable profile or verify the user's normal Codex profile",
    )
    canary_p.add_argument(
        "--confirm",
        default="",
        help="Exact confirmation phrase printed by the readiness report",
    )
    canary_p.add_argument("--db", default=None, help="SQLite database path")
    canary_p.add_argument(
        "--timeout", type=float, default=120, help="Maximum live invocation time in seconds"
    )
    canary_p.add_argument(
        "--output", default=None, help="Write the JSON report atomically to this path"
    )
    _bind(canary_p, handlers, "cmd_host_canary")


def _register_configuration(sub: Subparsers, handlers: Handlers) -> None:
    configure = sub.add_parser("configure", help="Guided setup wizard — writes agency.yaml")
    configure.add_argument(
        "--non-interactive",
        action="store_true",
        help="Write detected config without prompts",
    )
    configure.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=None,
        help="Security and capability profile to configure",
    )
    configure.add_argument("--force", action="store_true", help="Overwrite existing config")
    _bind(
        configure,
        handlers,
        "cmd_configure",
    )

    doctor = sub.add_parser("doctor", help="Check DB, config, providers, and adapter availability")
    doctor.add_argument("--json", action="store_true", help="JSON output")
    doctor.add_argument("--verbose", action="store_true", help="Include passing checks and detail")
    _bind(doctor, handlers, "cmd_doctor")

    config = sub.add_parser("config", help="Non-interactive config helpers")
    config_sub = config.add_subparsers(dest="config_command", required=True)

    config_show = config_sub.add_parser("show", help="Print effective config")
    config_show.add_argument("--raw", action="store_true", help="Show secrets")
    _bind(config_show, handlers, "cmd_config_show")

    config_path = config_sub.add_parser("path", help="Print config file location")
    _bind(config_path, handlers, "cmd_config_path")

    config_get = config_sub.add_parser("get", help="Get a config value")
    config_get.add_argument("key", help="Dotted key (e.g. judge.model)")
    config_get.add_argument("--raw", action="store_true", help="Show secret values")
    _bind(config_get, handlers, "cmd_config_get")

    config_set = config_sub.add_parser("set", help="Set a config value")
    config_set.add_argument("key", help="Dotted key (e.g. judge.model)")
    config_set.add_argument("value", nargs="?", help="YAML value to set (never use for secrets)")
    config_input = config_set.add_mutually_exclusive_group()
    config_input.add_argument(
        "--stdin", action="store_true", help="Read the value from standard input"
    )
    config_input.add_argument(
        "--prompt", action="store_true", help="Prompt without echo for a secret value"
    )
    config_input.add_argument("--clear", action="store_true", help="Clear a stored secret")
    _bind(
        config_set,
        handlers,
        "cmd_config_set",
    )

    config_provider = config_sub.add_parser(
        "provider",
        help="Configure the ordered inference provider chain",
    )
    provider_sub = config_provider.add_subparsers(
        dest="config_provider_command",
        required=True,
    )
    provider_list = provider_sub.add_parser("list", help="List configured providers")
    provider_list.add_argument("--json", action="store_true", help="Print JSON")
    _bind(provider_list, handlers, "cmd_config_provider_list")
    provider_models = provider_sub.add_parser(
        "models",
        help="Discover account-visible models for an authenticated CLI provider",
    )
    provider_models.add_argument(
        "transport",
        choices=["codex", "claude"],
        help="Authenticated CLI transport to inspect",
    )
    provider_models.add_argument("--refresh", action="store_true", help="Bypass the short cache")
    provider_models.add_argument("--json", action="store_true", help="Print JSON")
    provider_models.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Discovery timeout in seconds",
    )
    _bind(provider_models, handlers, "cmd_config_provider_models")
    provider_set = provider_sub.add_parser("set", help="Add or update a named provider")
    provider_set.add_argument("name", help="Stable provider name")
    provider_set.add_argument(
        "--type",
        choices=["openai", "openai-compatible", "anthropic", "ollama", "litellm", "cli"],
        default=None,
        help="Provider protocol (required when adding)",
    )
    provider_set.add_argument("--model", default=None, help="Model or LiteLLM router alias")
    provider_set.add_argument(
        "--reasoning-effort",
        choices=["default", "low", "medium", "high", "xhigh", "max", "ultra"],
        default=None,
        help="Codex subscription reasoning effort; 'default' clears the override",
    )
    provider_set.add_argument(
        "--transport",
        choices=["codex", "claude"],
        default=None,
        help="Authenticated CLI transport",
    )
    provider_set.add_argument("--base-url", default=None, help="Provider base URL")
    provider_set.add_argument(
        "--api-key-env",
        default=None,
        help="Environment variable containing the provider key",
    )
    provider_set.add_argument("--timeout", type=float, default=None, help="Timeout in seconds")
    _bind(
        provider_set,
        handlers,
        "cmd_config_provider_set",
    )
    provider_remove = provider_sub.add_parser("remove", help="Remove a named provider")
    provider_remove.add_argument("name", help="Provider name")
    _bind(
        provider_remove,
        handlers,
        "cmd_config_provider_remove",
    )

    config_validate = config_sub.add_parser("validate", help="Validate config + reachability")
    _bind(config_validate, handlers, "cmd_config_validate")

    config_reset = config_sub.add_parser("reset", help="Reset to defaults")
    _bind(
        config_reset,
        handlers,
        "cmd_config_reset",
    )


def _register_setup(sub: Subparsers, handlers: Handlers) -> None:
    setup = sub.add_parser(
        "setup",
        help="Guided first run — configure, install, diagnose, and smoke",
    )
    setup.add_argument(
        "--non-interactive",
        action="store_true",
        help="Use detected configuration without prompts (requires an explicit install scope)",
    )
    setup.add_argument(
        "--profile",
        choices=sorted(PROFILES),
        default=None,
        help="Security and capability profile used when configuration is created or replaced",
    )
    setup.add_argument(
        "--force-config",
        action="store_true",
        help="Replace an existing config through the guarded provider wizard",
    )
    setup_target = setup.add_mutually_exclusive_group()
    setup_target.add_argument(
        "--all",
        action="store_true",
        help="Install every safely detected supported harness",
    )
    setup_target.add_argument(
        "--agent",
        choices=list(HOSTS),
        default=None,
        help="Install one explicit supported harness",
    )
    setup_target.add_argument(
        "--skip-install",
        action="store_true",
        help="Skip harness and dashboard installation",
    )
    setup.add_argument(
        "--no-dashboard",
        action="store_true",
        help="Do not install or refresh the optional local dashboard service",
    )
    setup.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Skip deterministic readiness smoke checks",
    )
    _bind(setup, handlers, "cmd_setup")


def _register_roster(sub: Subparsers, handlers: Handlers) -> None:
    sync = sub.add_parser(
        "sync", help="Download sources into quarantine and create a roster snapshot"
    )
    sync.add_argument(
        "--dry-run", action="store_true", help="Fetch and validate without persisting a snapshot"
    )
    sync.add_argument("--review", action="store_true", help="Print the candidate diff after sync")
    sync.add_argument(
        "--auto-approve",
        action="store_true",
        help="Approve only candidates from explicitly trusted sources",
    )
    _bind(
        sync,
        handlers,
        "cmd_sync",
    )

    source = sub.add_parser("source", help="Manage roster sources")
    source_sub = source.add_subparsers(dest="source_command", required=True)
    source_add = source_sub.add_parser("add", help="Add a roster source")
    source_add.add_argument("url", help="HTTPS source URL")
    source_add.add_argument("--name", default="", help="Human-readable source name")
    source_add.add_argument(
        "--trusted-for-auto-approve",
        action="store_true",
        help="Allow this source to be used with sync --auto-approve automation",
    )
    _bind(
        source_add,
        handlers,
        "cmd_source_add",
    )
    source_list = source_sub.add_parser("list", help="List roster sources")
    _bind(source_list, handlers, "cmd_source_list")

    roster = sub.add_parser("roster", help="Inspect and activate roster snapshots")
    roster_sub = roster.add_subparsers(dest="roster_command", required=True)
    roster_list = roster_sub.add_parser("list", help="List active roster")
    _bind(roster_list, handlers, "cmd_roster_list")
    roster_diff = roster_sub.add_parser("diff", help="Create/show diff for quarantined candidates")
    roster_diff.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        roster_diff,
        handlers,
        "cmd_roster_diff",
    )
    roster_approve = roster_sub.add_parser("approve", help="Approve snapshot")
    roster_approve.add_argument("snapshot_id", help="Snapshot identifier to approve")
    _bind(
        roster_approve,
        handlers,
        "cmd_roster_approve",
    )
    roster_activate = roster_sub.add_parser("activate", help="Activate approved snapshot")
    roster_activate.add_argument("snapshot_id", help="Approved snapshot identifier to activate")
    _bind(
        roster_activate,
        handlers,
        "cmd_roster_activate",
    )
    roster_scans = roster_sub.add_parser(
        "scans",
        help="List complete and partial source-scan evidence",
    )
    roster_scans.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help="Maximum scan receipts to return",
    )
    _bind(roster_scans, handlers, "cmd_roster_scans")
    roster_remediation = roster_sub.add_parser(
        "remediation",
        help="Inspect quarantined source-repair attempts",
    )
    remediation_sub = roster_remediation.add_subparsers(
        dest="remediation_command",
        required=True,
    )
    remediation_queue = remediation_sub.add_parser(
        "queue",
        help="List bounded non-executable remediation receipts",
    )
    remediation_queue.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help="Maximum pending and resolved remediation records per page",
    )
    remediation_queue.add_argument(
        "--pending-cursor",
        default="",
        help="Continue pending attempts before this queue event identifier",
    )
    remediation_queue.add_argument(
        "--history-cursor",
        default="",
        help="Continue resolved history before this resolution event identifier",
    )
    _bind(remediation_queue, handlers, "cmd_roster_remediation_queue")
    roster_retire = roster_sub.add_parser(
        "retire",
        help="Create an unapproved retirement snapshot from a complete scan",
    )
    roster_retire.add_argument("slug", help="Active source-owned agent slug")
    roster_retire.add_argument(
        "--scan-id",
        required=True,
        help="Latest complete source scan proving the agent is absent",
    )
    roster_retire.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable snapshot details",
    )
    _bind(
        roster_retire,
        handlers,
        "cmd_roster_retire",
    )
    roster_rollback = roster_sub.add_parser(
        "rollback",
        help="Restore one immutable revision under an exact current-state check",
    )
    roster_rollback.add_argument("slug", help="Active agent slug")
    roster_rollback.add_argument("target_version", help="Immutable revision to restore")
    roster_rollback.add_argument(
        "--expected-current-version",
        required=True,
        help="Current version observed before requesting rollback",
    )
    roster_rollback.add_argument(
        "--expected-current-hash",
        required=True,
        help="Current prompt hash observed before requesting rollback",
    )
    roster_rollback.add_argument(
        "--json",
        action="store_true",
        help="Print the restored active record as JSON",
    )
    _bind(
        roster_rollback,
        handlers,
        "cmd_roster_rollback",
    )

    roster_upstream = roster_sub.add_parser(
        "upstream",
        help="Inspect or quarantine deltas from the audited upstream baseline",
    )
    upstream_sub = roster_upstream.add_subparsers(dest="upstream_command", required=True)
    upstream_status = upstream_sub.add_parser(
        "status",
        help="Compare configured sources without persistence",
    )
    upstream_status.add_argument("--source-id", default="", help="Inspect one enabled source")
    upstream_status.add_argument(
        "--source-revision",
        default="",
        help="Immutable source revision (defaults to packaged baseline revision)",
    )
    _bind(upstream_status, handlers, "cmd_roster_upstream_status")
    upstream_import = upstream_sub.add_parser(
        "import",
        help="Quarantine only new or content-changed definitions",
    )
    upstream_import.add_argument("--source-id", default="", help="Import one enabled source")
    upstream_import.add_argument(
        "--source-revision",
        default="",
        help="Immutable source revision (defaults to packaged baseline revision)",
    )
    upstream_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Compare and validate without writing quarantine evidence",
    )
    _bind(
        upstream_import,
        handlers,
        "cmd_roster_upstream_import",
    )

    roster_candidate = roster_sub.add_parser(
        "candidate",
        help="Audit, inspect, compare, or reject quarantined candidates",
    )
    candidate_sub = roster_candidate.add_subparsers(dest="candidate_command", required=True)
    candidate_audit = candidate_sub.add_parser(
        "audit",
        help="Run deterministic review plus configured inference",
    )
    candidate_audit.add_argument("candidate_id", help="Quarantined candidate identifier")
    candidate_audit.add_argument(
        "--require-inference",
        action="store_true",
        help="Fail closed unless an inference audit assistant is available",
    )
    _bind(
        candidate_audit,
        handlers,
        "cmd_roster_candidate_audit",
    )
    candidate_findings = candidate_sub.add_parser(
        "findings",
        help="Show immutable audit history and findings",
    )
    candidate_findings.add_argument("candidate_id", help="Candidate identifier")
    candidate_findings.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help="Maximum immutable audit records to return",
    )
    _bind(candidate_findings, handlers, "cmd_roster_candidate_findings")
    candidate_reject = candidate_sub.add_parser(
        "reject",
        help="Reject a candidate without changing the active revision",
    )
    candidate_reject.add_argument("candidate_id", help="Candidate identifier")
    candidate_reject.add_argument("--reason", required=True, help="Bounded review reason")
    _bind(
        candidate_reject,
        handlers,
        "cmd_roster_candidate_reject",
    )
    candidate_compare = candidate_sub.add_parser(
        "compare",
        help="Compare active and candidate metadata",
    )
    candidate_compare.add_argument("candidate_id", help="Candidate identifier")
    _bind(candidate_compare, handlers, "cmd_roster_candidate_compare")

    agents = sub.add_parser(
        "agents",
        help="List or toggle reversible per-agent routing availability",
    )
    agents_sub = agents.add_subparsers(dest="agents_command", required=True)
    agents_list = agents_sub.add_parser("list", help="List enabled, disabled, and protected agents")
    agents_list.add_argument("--json", action="store_true", help="Print machine-readable results")
    agents_list.add_argument(
        "--config",
        default=None,
        help="Configuration file (defaults to env, installed service identity, or user config)",
    )
    _bind(agents_list, handlers, "cmd_agents_list")
    agent_enable = agents_sub.add_parser(
        "enable", help="Enable an agent without changing roster data"
    )
    agent_enable.add_argument("slug", help="Governed agent slug")
    agent_enable.add_argument(
        "--config",
        default=None,
        help="Configuration file (defaults to env, installed service identity, or user config)",
    )
    _bind(
        agent_enable,
        handlers,
        "cmd_agent_enable",
    )
    agent_disable = agents_sub.add_parser(
        "disable",
        help="Disable a non-coordinator agent without deleting roster data",
    )
    agent_disable.add_argument("slug", help="Governed agent slug")
    agent_disable.add_argument(
        "--config",
        default=None,
        help="Configuration file (defaults to env, installed service identity, or user config)",
    )
    _bind(
        agent_disable,
        handlers,
        "cmd_agent_disable",
    )

    search = sub.add_parser("search", help="Search active roster")
    search.add_argument("query", help="Capability or specialist search text")
    search.add_argument("--limit", type=_search_limit, default=10, help="Maximum results (1-100)")
    search.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(search, handlers, "cmd_search")


def _register_selection(sub: Subparsers, handlers: Handlers) -> None:
    route = sub.add_parser("route", help="Route a task to candidate agents")
    route.add_argument("task", help="Task description to route")
    route.add_argument("--limit", type=_positive_int, default=5, help="Maximum specialists")
    route.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(route, handlers, "cmd_route")

    policy_p = sub.add_parser(
        "policy",
        help="Show companion policy and validate coverage against active roster",
    )
    policy_p.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(policy_p, handlers, "cmd_policy")

    explain = sub.add_parser("explain", help="Explain why specialists were selected for a task")
    explain.add_argument("task", help="Task description to explain")
    explain.add_argument("--session-id", default="", help="Session id for cache/stickiness context")
    explain.add_argument(
        "--limit",
        type=_positive_int,
        default=10,
        help="Number of candidates to include",
    )
    _bind(explain, handlers, "cmd_explain")


def _register_workforce(sub: Subparsers, handlers: Handlers) -> None:
    """Register durable workforce, contractor, and hiring evidence surfaces."""

    workforce = sub.add_parser("workforce", help="Inspect and manage Agency's workforce")
    workforce_sub = workforce.add_subparsers(dest="workforce_command", required=True)
    workforce_list = workforce_sub.add_parser("list", help="List workers in every lifecycle state")
    workforce_list.add_argument(
        "--state",
        choices=["contractor", "employee", "disabled", "suspended", "retired", "merged"],
        default="",
        help="Filter by the effective workforce lifecycle state",
    )
    workforce_list.add_argument(
        "--limit", type=_search_limit, default=100, help="Maximum workers to return"
    )
    workforce_list.add_argument("--after", default="", help="Continue after this worker slug")
    workforce_list.add_argument("--json", action="store_true", help="Print machine-readable output")
    workforce_list.add_argument(
        "--card",
        action="store_true",
        help="Render one card per worker (default when stdout is a TTY and --json is not set)",
    )
    _bind(workforce_list, handlers, "cmd_workforce_list")

    workforce_search = workforce_sub.add_parser(
        "search", help="Search normalized recruitment contracts"
    )
    workforce_search.add_argument("query", help="Terms to match against recruitment contracts")
    workforce_search.add_argument(
        "--state",
        choices=["contractor", "employee", "disabled", "suspended", "retired", "merged"],
        default="",
        help="Filter matches by lifecycle state",
    )
    workforce_search.add_argument(
        "--limit", type=_search_limit, default=20, help="Maximum matching workers to return"
    )
    workforce_search.add_argument(
        "--json", action="store_true", help="Print machine-readable output"
    )
    _bind(workforce_search, handlers, "cmd_workforce_search")

    duplicates = workforce_sub.add_parser(
        "duplicates",
        help="Compare one worker with the complete workforce without changing it",
    )
    duplicates.add_argument("worker", help="Stable worker ID or slug")
    duplicates.add_argument(
        "--limit", type=_search_limit, default=10, help="Maximum nearest workers to return"
    )
    duplicates.add_argument("--json", action="store_true", help="Print machine-readable output")
    _bind(duplicates, handlers, "cmd_workforce_duplicates")

    consolidate = workforce_sub.add_parser(
        "consolidate",
        help="List evidence-based amendment or merge candidates without changing them",
    )
    consolidate.add_argument(
        "--limit", type=_search_limit, default=25, help="Maximum review candidates to return"
    )
    consolidate.add_argument("--json", action="store_true", help="Print machine-readable output")
    _bind(consolidate, handlers, "cmd_workforce_consolidate")

    workforce_show = workforce_sub.add_parser(
        "show", help="Show contract, lineage, lifecycle, and outcome evidence"
    )
    workforce_show.add_argument("worker", help="Stable worker ID or slug")
    workforce_show.add_argument(
        "--limit", type=_search_limit, default=100, help="Maximum evidence events to return"
    )
    workforce_show.add_argument("--json", action="store_true", help="Print machine-readable output")
    _bind(workforce_show, handlers, "cmd_workforce_show")

    workforce_prompt = workforce_sub.add_parser(
        "prompt", help="Show an exact governed prompt with immutable source lineage"
    )
    workforce_prompt.add_argument("worker", help="Stable worker ID or slug")
    workforce_prompt.add_argument(
        "--version",
        default="",
        help="Exact historical workforce version (default: current)",
    )
    workforce_prompt.add_argument(
        "--max-chars",
        type=_positive_int,
        default=262_144,
        help="Maximum prompt characters to return (maximum: 262144)",
    )
    workforce_prompt.add_argument(
        "--json", action="store_true", help="Print machine-readable output"
    )
    _bind(workforce_prompt, handlers, "cmd_workforce_prompt")

    for action in ("promote", "suspend", "resume", "retire"):
        action_parser = workforce_sub.add_parser(action, help=f"{action.title()} a worker")
        action_parser.set_defaults(workforce_action=action)
        action_parser.add_argument("worker", help="Stable worker ID or slug")
        action_parser.add_argument(
            "--expected-revision", type=int, required=True, help="Current worker revision"
        )
        action_parser.add_argument("--reason", required=True, help="Durable reason for the change")
        if action in {"suspend", "retire"}:
            action_parser.add_argument(
                "--confirm",
                required=True,
                help=f"Exact confirmation: {action.upper()} <slug>",
            )
        action_parser.add_argument(
            "--json", action="store_true", help="Print machine-readable output"
        )
        _bind(
            action_parser,
            handlers,
            "cmd_workforce_transition",
        )

    merge = workforce_sub.add_parser("merge", help="Merge a worker into a coherent survivor")
    merge.set_defaults(workforce_action="merge")
    merge.add_argument("worker", help="Worker to merge")
    merge.add_argument("--into", required=True, help="Surviving worker slug")
    merge.add_argument(
        "--expected-revision", type=int, required=True, help="Current revision of the merged worker"
    )
    merge.add_argument("--reason", required=True, help="Durable evidence for the coherent merge")
    merge.add_argument(
        "--confirm",
        required=True,
        help="Exact confirmation: MERGE <slug> INTO <survivor>",
    )
    merge.add_argument("--json", action="store_true", help="Print machine-readable output")
    _bind(
        merge,
        handlers,
        "cmd_workforce_transition",
    )

    amend = workforce_sub.add_parser(
        "amend",
        help="Approve and apply an inference-produced governed amendment case",
    )
    amend.add_argument("case_id", help="Stable amendment hiring-case ID")
    amend.add_argument("--approved-by", required=True, help="Auditable operator identity")
    amend.add_argument("--confirm", required=True, help="Exact confirmation: APPROVE <case-id>")
    amend.add_argument("--json", action="store_true", help="Print machine-readable output")
    _bind(
        amend,
        handlers,
        "cmd_hiring_approve",
    )

    for action, handler in (("enable", "cmd_agent_enable"), ("disable", "cmd_agent_disable")):
        toggle = workforce_sub.add_parser(action, help=f"{action.title()} workforce routing")
        toggle.add_argument("slug", help="Governed worker slug")
        toggle.add_argument("--config", default=None, help="Override the Agency config path")
        toggle.add_argument("--reason", required=True, help="Durable reason for the change")
        toggle.add_argument(
            "--confirm",
            required=True,
            help=f"Exact confirmation: {action.upper()} <slug>",
        )
        toggle.add_argument("--json", action="store_true", help="Print machine-readable output")
        _bind(
            toggle,
            handlers,
            handler,
        )

    contractor = sub.add_parser("contractor", help="Inspect newly hired contractors")
    contractor_sub = contractor.add_subparsers(dest="contractor_command", required=True)
    contractor_list = contractor_sub.add_parser("list", help="List active contractors")
    contractor_list.add_argument(
        "--limit", type=_search_limit, default=100, help="Maximum contractors to return"
    )
    contractor_list.add_argument("--after", default="", help="Continue after this worker slug")
    contractor_list.add_argument(
        "--json", action="store_true", help="Print machine-readable output"
    )
    _bind(contractor_list, handlers, "cmd_contractor_list")
    contractor_show = contractor_sub.add_parser("show", help="Show contractor evidence")
    contractor_show.add_argument("worker", help="Stable contractor worker ID or slug")
    contractor_show.add_argument(
        "--limit", type=_search_limit, default=100, help="Maximum evidence events to return"
    )
    contractor_show.add_argument(
        "--json", action="store_true", help="Print machine-readable output"
    )
    _bind(contractor_show, handlers, "cmd_workforce_show")

    hiring = sub.add_parser("hiring", help="Inspect and approve governed hiring evidence")
    hiring_sub = hiring.add_subparsers(dest="hiring_command", required=True)
    hiring_list = hiring_sub.add_parser("list", help="List hiring and amendment cases")
    hiring_list.add_argument(
        "--status",
        choices=["proposed", "audited", "rejected", "applied", "folded"],
        default="",
        help="Filter by hiring decision state",
    )
    hiring_list.add_argument(
        "--type", choices=["hire", "amend"], default="", help="Filter hires or amendments"
    )
    hiring_list.add_argument(
        "--limit", type=_search_limit, default=100, help="Maximum hiring cases to return"
    )
    hiring_list.add_argument("--json", action="store_true", help="Print machine-readable output")
    hiring_list.add_argument(
        "--card",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=("Render one card per case (default when stdout is a TTY and --json is not set)"),
    )
    _bind(hiring_list, handlers, "cmd_hiring_list")
    hiring_show = hiring_sub.add_parser("show", help="Show complete hiring evidence")
    hiring_show.add_argument("case_id", help="Stable hiring case ID")
    hiring_show.add_argument("--json", action="store_true", help="Print machine-readable output")
    hiring_show.add_argument(
        "--card",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Render one card with title, fields, and evidence sections "
            "(default when stdout is a TTY and --json is not set)"
        ),
    )
    _bind(hiring_show, handlers, "cmd_hiring_show")
    hiring_approve = hiring_sub.add_parser(
        "approve", help="Approve a high-risk proposed hire before audit"
    )
    hiring_approve.add_argument("case_id", help="High-risk proposed hiring case ID")
    hiring_approve.add_argument("--approved-by", required=True, help="Auditable operator identity")
    hiring_approve.add_argument(
        "--confirm", required=True, help="Exact confirmation: APPROVE <case-id>"
    )
    hiring_approve.add_argument("--json", action="store_true", help="Print machine-readable output")
    _bind(
        hiring_approve,
        handlers,
        "cmd_hiring_approve",
    )


def _register_delegation_and_evals(sub: Subparsers, handlers: Handlers) -> None:
    eval_p = sub.add_parser("eval", help="Run deterministic eval suites")
    eval_sub = eval_p.add_subparsers(dest="eval_command", required=True)
    eval_host_parity = eval_sub.add_parser(
        "host-parity",
        help="Prove every adapter records the same evidence for an identical turn",
    )
    eval_host_parity.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    _bind(eval_host_parity, handlers, "cmd_eval_host_parity")
    eval_spawn_authority = eval_sub.add_parser(
        "spawn-authority",
        help="Prove at the source that only the host may start an agent",
    )
    eval_spawn_authority.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    _bind(eval_spawn_authority, handlers, "cmd_eval_spawn_authority")
    eval_staffing = eval_sub.add_parser(
        "staffing",
        help="Measure staffing rate, recruiter cost, and the cold budget",
    )
    eval_staffing.add_argument("--json", action="store_true", help="Print machine-readable results")
    eval_staffing.add_argument(
        "--no-details", action="store_true", help="Omit the per-ask manifest"
    )
    _bind(eval_staffing, handlers, "cmd_eval_staffing")
    eval_routing = eval_sub.add_parser(
        "routing",
        help="Run versioned routing and latency gates",
    )
    eval_routing.add_argument("--json", action="store_true", help="Print machine-readable results")
    eval_routing.add_argument(
        "--no-details",
        action="store_true",
        help="Omit per-case details from the report",
    )
    _bind(eval_routing, handlers, "cmd_eval_routing")
    eval_decision_conformance = eval_sub.add_parser(
        "decision-conformance",
        help="Prove focused tests kill curated routing and workforce decision mutations",
    )
    eval_decision_conformance.add_argument(
        "--repository",
        default=".",
        help="Agency Runtime repository root to copy and evaluate",
    )
    eval_decision_conformance.add_argument(
        "--timeout",
        type=_positive_int,
        default=90,
        help="Per-test deadline in seconds (1 through 300)",
    )
    eval_decision_conformance.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable mutation evidence",
    )
    _bind(
        eval_decision_conformance,
        handlers,
        "cmd_eval_decision_conformance",
    )
    eval_full_roster = eval_sub.add_parser(
        "full-roster",
        help="Evaluate complete packaged-roster retrieval and compatibility contracts",
    )
    eval_full_roster.add_argument(
        "--candidate-limit",
        type=_positive_int,
        default=40,
        help="Bounded candidate-union size (supported range: 8 through 80)",
    )
    eval_full_roster.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    eval_full_roster.add_argument(
        "--no-details",
        action="store_true",
        help="Omit per-case details from the report",
    )
    _bind(eval_full_roster, handlers, "cmd_eval_full_roster")
    eval_shadow_recall = eval_sub.add_parser(
        "shadow-recall",
        help="Run the fixed live AR-266 four-host shadow-value matrix",
    )
    eval_shadow_recall.add_argument(
        "--confirm-live-inference",
        default="",
        help='Required exact phrase: "RUN LIVE SHADOW RECALL EVAL"',
    )
    eval_shadow_recall.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    eval_shadow_recall.add_argument(
        "--no-details",
        action="store_true",
        help="Omit per-host and per-case matrix details",
    )
    _bind(eval_shadow_recall, handlers, "cmd_eval_shadow_recall")
    eval_upstream_architecture = eval_sub.add_parser(
        "upstream-architecture",
        help="Compare Agency's explicit contracts with a pinned upstream orchestrator",
    )
    eval_upstream_architecture.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    _bind(
        eval_upstream_architecture,
        handlers,
        "cmd_eval_upstream_architecture",
    )
    eval_upstream_selection = eval_sub.add_parser(
        "upstream-selection",
        help="Run a matched held-out selection benchmark against pinned upstream Agency Agents",
    )
    eval_upstream_selection.add_argument(
        "--all",
        action="store_true",
        help=f"Run all {len(UPSTREAM_SELECTION_CASES)} held-out matched cases",
    )
    eval_upstream_selection.add_argument(
        "--case",
        action="append",
        choices=tuple(case.case_id for case in UPSTREAM_SELECTION_CASES),
        default=[],
        help="Run only this held-out case; repeat to run a bounded subset",
    )
    eval_upstream_selection.add_argument(
        "--host",
        choices=("codex", "claude", "openclaw", "hermes", "zcode"),
        default="codex",
        help="Execution host contract shared by both selection arms",
    )
    eval_upstream_selection.add_argument(
        "--platform",
        choices=("windows", "linux"),
        required=True,
        help="Target operating system contract shared by both selection arms",
    )
    eval_upstream_selection.add_argument(
        "--available-tool",
        action="append",
        default=[],
        help=(
            "Optionally restrict shared tool capabilities; by default every audited "
            "roster tool class is visible to both arms"
        ),
    )
    eval_upstream_selection.add_argument(
        "--confirm-live-inference",
        default="",
        help='Required exact phrase: "RUN MATCHED UPSTREAM SELECTION EVAL"',
    )
    eval_upstream_selection.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable matched results",
    )
    eval_upstream_selection.add_argument(
        "--no-details",
        action="store_true",
        help="Omit per-case matched selection details",
    )
    _bind(
        eval_upstream_selection,
        handlers,
        "cmd_eval_upstream_selection",
    )
    eval_workforce = eval_sub.add_parser(
        "workforce",
        help="Run a configured-inference workforce selection corpus (may incur provider cost)",
    )
    eval_workforce.add_argument(
        "--all",
        action="store_true",
        help=f"Run all {len(CASES)} configured-inference cases",
    )
    eval_workforce.add_argument(
        "--case",
        action="append",
        choices=tuple(case.case_id for case in CASES),
        default=[],
        help="Run only this case; repeat to run a bounded subset",
    )
    eval_workforce.add_argument(
        "--host",
        choices=("codex", "claude", "openclaw", "hermes", "zcode"),
        default="codex",
        help="Execution host contract to grade",
    )
    eval_workforce.add_argument(
        "--platform",
        choices=("windows", "linux"),
        required=True,
        help="Target operating system contract",
    )
    eval_workforce.add_argument(
        "--available-tool",
        action="append",
        default=[],
        help="Repeat for each capability available to planned work units",
    )
    eval_workforce.add_argument(
        "--confirm-live-inference",
        default="",
        help='Required exact phrase: "RUN LIVE WORKFORCE EVAL"',
    )
    eval_workforce.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    eval_workforce.add_argument(
        "--no-details", action="store_true", help="Omit per-case selection details"
    )
    _bind(eval_workforce, handlers, "cmd_eval_workforce")
    eval_product = eval_sub.add_parser(
        "product",
        help="Run one exact-confirmed one-shot product build (may incur host/model cost)",
    )
    eval_product.add_argument(
        "--scenario",
        choices=tuple(PRODUCT_SCENARIOS_BY_ID),
        required=True,
        help="Versioned application contract to build and grade",
    )
    eval_product.add_argument(
        "--trial-id",
        required=True,
        help="Stable lowercase trial identifier used in the evidence report",
    )
    eval_product.add_argument(
        "--host",
        choices=("codex", "claude", "openclaw", "hermes", "zcode"),
        required=True,
        help="Native agent host to execute",
    )
    eval_product.add_argument(
        "--mode",
        choices=("agency", "native-only"),
        required=True,
        help="Run with Agency enabled or as a native-host baseline",
    )
    eval_product.add_argument(
        "--workspace",
        required=True,
        help="Existing empty real directory that will receive the generated application",
    )
    eval_product.add_argument(
        "--timeout",
        type=float,
        default=1800.0,
        help="End-to-end host deadline in seconds (600 through 3600)",
    )
    eval_product.add_argument(
        "--model",
        default="",
        help="Optional native-host model request; actual model remains receipt-gated",
    )
    eval_product.add_argument(
        "--confirm-live-product-eval",
        default="",
        help="Exact phrase: RUN LIVE PRODUCT EVAL <scenario> <host> <mode>",
    )
    eval_product.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(eval_product, handlers, "cmd_eval_product")
    eval_compare = eval_sub.add_parser(
        "compare",
        help="Validate and summarize bounded paired native/Agency outcome evidence",
    )
    eval_compare.add_argument(
        "--input",
        required=True,
        help="UTF-8 JSONL file containing blinded comparative observations",
    )
    _bind(eval_compare, handlers, "cmd_eval_compare")

    battery = sub.add_parser(
        "battery",
        help="Run the change-triggered harness canary battery",
    )
    battery.add_argument(
        "--host",
        choices=["claude", "codex", "hermes", "openclaw"],
        help="Limit the battery to one harness",
    )
    battery.add_argument(
        "--force",
        action="store_true",
        help="Run the battery even without a version change",
    )
    battery.add_argument(
        "--baseline",
        action="store_true",
        help="Adopt current harness versions as the proven baseline without running",
    )
    battery.add_argument(
        "--install-service",
        action="store_true",
        help="Install and enable the systemd-user path and timer triggers",
    )
    battery.add_argument(
        "--uninstall-service",
        action="store_true",
        help="Disable and remove the systemd-user battery triggers",
    )
    battery.add_argument(
        "--trials",
        type=_battery_trials,
        default=None,
        help=(
            f"Trials per host probe, 1 through {BATTERY_MAX_TRIALS} "
            f"(default {BATTERY_DEFAULT_TRIALS}); canaries grade pass^k, "
            "ordinary checks pass@k"
        ),
    )
    battery.add_argument(
        "--config",
        help="Explicit Agency configuration path",
    )
    battery.add_argument(
        "--json",
        action="store_true",
        help="Print the machine-readable battery report",
    )
    _bind(battery, handlers, "cmd_battery")


def _register_chaos(sub: Subparsers, handlers: Handlers) -> None:
    from agency_runtime.core.chaos import CHAOS_EXPERIMENT_NAMES

    chaos = sub.add_parser(
        "chaos",
        help="Inject one owned fault into a dedicated runtime and judge it with an oracle",
    )
    chaos_sub = chaos.add_subparsers(dest="chaos_command", required=True)
    run = chaos_sub.add_parser(
        "run",
        help="Run chaos experiments in a rolled-back dedicated runtime and seal receipts",
    )
    run.add_argument(
        "--experiment",
        action="append",
        choices=CHAOS_EXPERIMENT_NAMES,
        default=None,
        help="Run one named experiment (repeatable; default: every experiment)",
    )
    run.add_argument("--json", action="store_true", help="Print the machine-readable report")
    _bind(run, handlers, "cmd_chaos_run")

    smoke = sub.add_parser("smoke", help="Run deterministic local smoke checks")
    smoke.add_argument(
        "--all",
        action="store_true",
        help="Smoke-test every supported generated host plugin",
    )
    smoke.add_argument(
        "--agent",
        choices=["codex", "claude", "zcode", "hermes", "openclaw"],
        help="Smoke-test one host's generated plugin",
    )
    smoke.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(smoke, handlers, "cmd_smoke")


def _register_database(sub: Subparsers, handlers: Handlers) -> None:
    db_p = sub.add_parser("db", help="Inspect and trim the SQLite store")
    db_sub = db_p.add_subparsers(dest="db_command", required=True)
    db_stats = db_sub.add_parser("stats", help="Show row counts and file sizes")
    db_stats.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(db_stats, handlers, "cmd_db_stats")
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
    db_trim.add_argument("--no-vacuum", action="store_true", help="Skip VACUUM after deleting rows")
    db_trim.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        db_trim,
        handlers,
        "cmd_db_trim",
    )


def _register_native_protocols(sub: Subparsers, handlers: Handlers) -> None:
    mcp = sub.add_parser("mcp", help="Serve MCP over stdin/stdout")
    mcp.add_argument("--db", default=None, help="SQLite database path")
    mcp.add_argument("--config", default=None, help="Agency YAML configuration path")
    _bind(mcp, handlers, "cmd_mcp")

    hook = sub.add_parser("hook", help="Handle one native host hook event")
    hook.add_argument("host", choices=["codex", "claude", "zcode"], help="Native hook protocol")
    hook.add_argument(
        "--event",
        choices=_NATIVE_HOOK_EVENTS,
        default="",
        help="Installer-bound native event discriminator",
    )
    hook.add_argument("--db", default=None, help="SQLite database path")
    hook.add_argument("--config", default=None, help="Agency YAML configuration path")
    hook.add_argument(
        "--runtime-control",
        default=None,
        help="Installer-bound Agency master-control path",
    )
    _bind(hook, handlers, "cmd_hook")


def _register_dashboard_service_actions(
    dashboard_service: argparse.ArgumentParser,
    handlers: Handlers,
) -> None:
    service_sub = dashboard_service.add_subparsers(
        dest="dashboard_service_action",
        required=True,
    )
    action_help = {
        "status": "Inspect registration, process, endpoint, and descriptor state",
        "start": "Start the registered current-user dashboard service",
        "stop": "Stop the current-user dashboard service",
        "restart": "Restart the current-user dashboard service",
        "uninstall": "Stop and unregister the owned dashboard service",
    }
    for action, help_text in action_help.items():
        action_parser = service_sub.add_parser(action, help=help_text)
        action_parser.add_argument(
            "--json", action="store_true", help="Print machine-readable results"
        )
        if action == "status":
            _bind(action_parser, handlers, "cmd_dashboard_service")
        else:
            _bind(
                action_parser,
                handlers,
                "cmd_dashboard_service",
            )
    install = service_sub.add_parser(
        "install", help="Register and start the current-user dashboard service"
    )
    install.add_argument(
        "--dry-run", action="store_true", help="Print the service plan without changing the host"
    )
    install.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        install,
        handlers,
        "cmd_dashboard_service",
    )
    open_p = service_sub.add_parser("open", help="Resolve and open the live authenticated URL")
    open_p.add_argument(
        "--no-open", action="store_true", help="Print status without launching a browser"
    )
    open_p.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(
        open_p,
        handlers,
        "cmd_dashboard_service",
    )


def _register_services(sub: Subparsers, handlers: Handlers) -> None:
    serve_p = sub.add_parser("serve", help="Start HTTP server")
    _bind(serve_p, handlers, "cmd_serve")

    dashboard = sub.add_parser("dashboard", help="Open the secure local operations dashboard")
    dashboard.add_argument(
        "--port",
        type=int,
        default=0,
        help="Loopback port (default: choose a free port)",
    )
    dashboard.add_argument("--db", default=None, help="SQLite database path")
    dashboard.add_argument("--no-open", action="store_true", help="Do not open a web browser")
    dashboard.add_argument("--service-mode", action="store_true", help=argparse.SUPPRESS)
    dashboard.add_argument("--config", default=None, help=argparse.SUPPRESS)
    dashboard_sub = dashboard.add_subparsers(dest="dashboard_command")
    dashboard_service = dashboard_sub.add_parser(
        "service",
        help="Manage the optional per-user dashboard service",
    )
    _register_dashboard_service_actions(dashboard_service, handlers)
    _bind(dashboard, handlers, "cmd_dashboard")


def _register_evidence(sub: Subparsers, handlers: Handlers) -> None:
    evidence = sub.add_parser(
        "evidence",
        help="Read source-labelled evidence from host artifacts or Agency's Store",
    )
    evidence_sub = evidence.add_subparsers(dest="evidence_command", required=True)
    children = evidence_sub.add_parser(
        "children",
        help="Show which harness-spawned children provably received a specialist card",
    )
    children.add_argument(
        "--host",
        choices=("claude", "codex"),
        default=None,
        help="Read one host only (default: every host that writes child artifacts)",
    )
    children.add_argument(
        "--root",
        default=None,
        help="Read this artifact root instead of the host's own (requires --host)",
    )
    children.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help=(f"Newest verified details per host (default: 50, max: {MAX_CHILD_DETAIL_RESULTS})"),
    )
    children.add_argument("--json", action="store_true", help="Print JSON")
    _bind(children, handlers, "cmd_evidence_children")
    child_launches = evidence_sub.add_parser(
        "child-launches",
        help="Show one outcome per harness-spawned child launch: staffed, declined, or unrecorded",
    )
    child_launches.add_argument(
        "--host",
        choices=("claude", "codex"),
        default=None,
        help="Read one host only (default: every host that writes child artifacts)",
    )
    child_launches.add_argument(
        "--root",
        default=None,
        help="Read this artifact root instead of the host's own (requires --host)",
    )
    child_launches.add_argument(
        "--since",
        default=None,
        help=(
            "Only count launches at or after this ISO-8601 instant. An artifact "
            "root holds children from every runtime that ever ran here, so an "
            "unscoped rate describes runtimes that never saw them."
        ),
    )
    child_launches.add_argument("--db", default=None, help="Read this Store instead of the default")
    child_launches.add_argument(
        "--limit",
        type=_positive_int,
        default=MAX_CHILD_LAUNCHES,
        help=f"Child artifacts scanned per host (default and max: {MAX_CHILD_LAUNCHES})",
    )
    child_launches.add_argument("--json", action="store_true", help="Print JSON")
    _bind(child_launches, handlers, "cmd_evidence_child_launches")
    rejections = evidence_sub.add_parser(
        "rejections",
        help="Partition recent exceptional runs into withheld and Agency-blind",
    )
    rejections.add_argument(
        "--host",
        choices=EXECUTION_HOSTS,
        default=None,
        help="Read one host only (default: every host that closed a turn)",
    )
    rejections.add_argument(
        "--limit",
        type=_positive_int,
        default=50,
        help=(
            f"Most recent N matching exceptional runs (default: 50, max: {MAX_RULE8_EVIDENCE_ROWS})"
        ),
    )
    rejections.add_argument(
        "--db",
        default=None,
        help="Read this evidence store instead of the configured one",
    )
    rejections.add_argument("--json", action="store_true", help="Print JSON")
    _bind(rejections, handlers, "cmd_evidence_rejections")
    latency = evidence_sub.add_parser(
        "latency",
        help="Show recorded routing durations against a p95 budget",
    )
    latency.add_argument(
        "--source",
        default=None,
        help="Read one decision source only (default: every source)",
    )
    latency.add_argument(
        "--limit",
        type=int,
        default=200,
        help="Most recent N decisions with a recorded latency (default: 200, max: 1000)",
    )
    latency.add_argument(
        "--budget-ms",
        type=int,
        default=15000,
        help="p95 budget in milliseconds; exit 1 when exceeded (default: 15000)",
    )
    latency.add_argument(
        "--db",
        default=None,
        help="Read this evidence store instead of the configured one",
    )
    latency.add_argument("--json", action="store_true", help="Print JSON")
    _bind(latency, handlers, "cmd_evidence_latency")
    selections = evidence_sub.add_parser(
        "selections",
        help="Show bounded specialist-selection frequency with explicit denominators",
    )
    selections.add_argument(
        "--db",
        default=None,
        help="Read this evidence store instead of the configured one",
    )
    selections.add_argument("--json", action="store_true", help="Print JSON")
    _bind(selections, handlers, "cmd_evidence_selections")
    intent = evidence_sub.add_parser(
        "intent",
        help="Audit what each turn was understood to be, against who was staffed",
    )
    intent.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Most recent N retained decisions (default: 20, max: 500)",
    )
    intent.add_argument(
        "--specialist",
        default=None,
        help="Show only turns that staffed this specialist",
    )
    intent.add_argument(
        "--db",
        default=None,
        help="Read this evidence store instead of the configured one",
    )
    intent.add_argument("--json", action="store_true", help="Print JSON")
    _bind(intent, handlers, "cmd_evidence_intent")
    staffing = evidence_sub.add_parser(
        "staffing",
        help="Measure the staffing-verdict window: turns, fail-open rate, dominant stage",
    )
    staffing.add_argument(
        "--host",
        choices=EXECUTION_HOSTS,
        default=None,
        help="Measure one host only (default: every host)",
    )
    staffing.add_argument(
        "--since",
        default=None,
        help="Window start as an ISO-8601 instant (default: the last --hours)",
    )
    staffing.add_argument(
        "--hours",
        type=_positive_int,
        default=None,
        help="Window length in hours when --since is absent (default: 24, max: 720)",
    )
    staffing.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Most recent N failure receipts to read (default: 500, max: 2000)",
    )
    staffing.add_argument(
        "--db",
        default=None,
        help="Read this evidence store instead of the configured one",
    )
    staffing.add_argument("--json", action="store_true", help="Print JSON")
    _bind(staffing, handlers, "cmd_evidence_staffing")
    context_budget = evidence_sub.add_parser(
        "context-budget",
        help="Size Agency's per-turn frame (kernel, policy, snapshots, capsule) in tokens",
    )
    context_budget.add_argument(
        "--host",
        choices=EXECUTION_HOSTS,
        default="claude",
        help="Host whose delivery shape to size (default: claude)",
    )
    context_budget.add_argument(
        "--sample",
        type=_positive_int,
        default=None,
        help="Newest ready turns to replay for the staffed capsule size (default: 100)",
    )
    context_budget.add_argument(
        "--estimator",
        choices=("auto", "chars", "tiktoken"),
        default="auto",
        help="Token estimator: chars/4 heuristic, tiktoken if importable, or auto",
    )
    context_budget.add_argument(
        "--db",
        default=None,
        help="Read this evidence store instead of the configured one",
    )
    context_budget.add_argument("--json", action="store_true", help="Print JSON")
    _bind(context_budget, handlers, "cmd_evidence_context_budget")
    wiring = evidence_sub.add_parser(
        "wiring",
        help="Check that each host invokes the projection the installer staged",
    )
    wiring.add_argument(
        "--host",
        choices=tuple(HOSTS),
        default=None,
        help="Check one host only (unsupported measurements report not_measured)",
    )
    wiring.add_argument("--json", action="store_true", help="Print JSON")
    _bind(wiring, handlers, "cmd_evidence_wiring")
    witness = evidence_sub.add_parser(
        "witness",
        help="Attest that each host's invoked projection carries every documented fix",
    )
    witness.add_argument(
        "--host",
        choices=tuple(HOSTS),
        default=None,
        help="Attest one host only (default: every host with a recorded install)",
    )
    witness.add_argument("--json", action="store_true", help="Print JSON")
    _bind(witness, handlers, "cmd_evidence_witness")


def build_parser(handlers: Handlers) -> argparse.ArgumentParser:
    """Build the command tree with callbacks supplied by the public facade."""
    parser = argparse.ArgumentParser(prog="agency", description="Agency Runtime Control Plane")
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the installed Agency Runtime version and exit",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _register_updates(sub, handlers)
    _register_install(sub, handlers)
    _register_uninstall(sub, handlers)
    _register_host_control(sub, handlers)
    _register_configuration(sub, handlers)
    _register_setup(sub, handlers)
    _register_roster(sub, handlers)
    _register_workforce(sub, handlers)
    _register_selection(sub, handlers)
    _register_delegation_and_evals(sub, handlers)
    _register_evidence(sub, handlers)
    _register_chaos(sub, handlers)
    _register_database(sub, handlers)
    _register_native_protocols(sub, handlers)
    _register_services(sub, handlers)
    return parser
