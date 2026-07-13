"""Declarative argparse construction independent of command implementations."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping

from agency_runtime.core.policy.profiles import PROFILES

CommandHandler = Callable[[argparse.Namespace], int]
Handlers = Mapping[str, CommandHandler]
Subparsers = argparse._SubParsersAction


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _bind(parser: argparse.ArgumentParser, handlers: Handlers, name: str) -> None:
    parser.set_defaults(func=handlers[name])


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
    install.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(install, handlers, "cmd_install")


def _register_host_control(sub: Subparsers, handlers: Handlers) -> None:
    on_p = sub.add_parser("on", help="Enable Agency Runtime for a host")
    on_p.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude"],
        default=None,
        help="Host to enable (default: every detected host)",
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
    _bind(on_p, handlers, "cmd_on")

    off_p = sub.add_parser("off", help="Disable Agency Runtime for a host")
    off_p.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude"],
        default=None,
        help="Host to disable (default: every detected host)",
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
    _bind(off_p, handlers, "cmd_off")

    status_p = sub.add_parser(
        "status", help="Show native and runtime control state for agent hosts"
    )
    status_p.add_argument(
        "--agent",
        choices=["hermes", "openclaw", "codex", "claude"],
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
        "agent", choices=["hermes", "openclaw", "codex", "claude"], help="Host to verify"
    )
    canary_p.add_argument(
        "--execute",
        action="store_true",
        help="Run the isolated live invocation after readiness inspection",
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
    _bind(configure, handlers, "cmd_configure")

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
    _bind(config_set, handlers, "cmd_config_set")

    config_validate = config_sub.add_parser("validate", help="Validate config + reachability")
    _bind(config_validate, handlers, "cmd_config_validate")

    config_reset = config_sub.add_parser("reset", help="Reset to defaults")
    _bind(config_reset, handlers, "cmd_config_reset")


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
    _bind(sync, handlers, "cmd_sync")

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
    _bind(source_add, handlers, "cmd_source_add")
    source_list = source_sub.add_parser("list", help="List roster sources")
    _bind(source_list, handlers, "cmd_source_list")

    roster = sub.add_parser("roster", help="Inspect and activate roster snapshots")
    roster_sub = roster.add_subparsers(dest="roster_command", required=True)
    roster_list = roster_sub.add_parser("list", help="List active roster")
    _bind(roster_list, handlers, "cmd_roster_list")
    roster_diff = roster_sub.add_parser("diff", help="Create/show diff for quarantined candidates")
    roster_diff.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(roster_diff, handlers, "cmd_roster_diff")
    roster_approve = roster_sub.add_parser("approve", help="Approve snapshot")
    roster_approve.add_argument("snapshot_id", help="Snapshot identifier to approve")
    _bind(roster_approve, handlers, "cmd_roster_approve")
    roster_activate = roster_sub.add_parser("activate", help="Activate approved snapshot")
    roster_activate.add_argument("snapshot_id", help="Approved snapshot identifier to activate")
    _bind(roster_activate, handlers, "cmd_roster_activate")

    search = sub.add_parser("search", help="Search active roster")
    search.add_argument("query", help="Capability or specialist search text")
    search.add_argument("--limit", type=_positive_int, default=10, help="Maximum results")
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


def _register_delegation_and_evals(sub: Subparsers, handlers: Handlers) -> None:
    delegate = sub.add_parser("delegate", help="Delegate a task to a backend")
    delegate.add_argument(
        "--backend",
        choices=["codex", "claude", "hermes", "openclaw", "generic"],
        default="generic",
        help="Execution backend",
    )
    delegate.add_argument("--agent", default="", help="Selected specialist slug or identifier")
    delegate.add_argument("--task", required=True, help="Bounded task description")
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
    _bind(delegate, handlers, "cmd_delegate")

    eval_p = sub.add_parser("eval", help="Run deterministic eval suites")
    eval_sub = eval_p.add_subparsers(dest="eval_command", required=True)
    eval_delegation = eval_sub.add_parser(
        "delegation", help="Run delegation lifecycle/evidence evals"
    )
    eval_delegation.add_argument(
        "--json", action="store_true", help="Print machine-readable results"
    )
    _bind(eval_delegation, handlers, "cmd_eval_delegation")
    eval_routing = eval_sub.add_parser(
        "routing",
        help="Run versioned routing, policy, delegation, and latency gates",
    )
    eval_routing.add_argument("--json", action="store_true", help="Print machine-readable results")
    eval_routing.add_argument(
        "--no-details",
        action="store_true",
        help="Omit per-case details from the report",
    )
    _bind(eval_routing, handlers, "cmd_eval_routing")

    smoke = sub.add_parser("smoke", help="Run deterministic local smoke checks")
    smoke.add_argument(
        "--all",
        action="store_true",
        help="Smoke-test every supported generated host plugin",
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
    _bind(db_trim, handlers, "cmd_db_trim")


def _register_native_protocols(sub: Subparsers, handlers: Handlers) -> None:
    mcp = sub.add_parser("mcp", help="Serve MCP over stdin/stdout")
    mcp.add_argument("--db", default=None, help="SQLite database path")
    _bind(mcp, handlers, "cmd_mcp")

    hook = sub.add_parser("hook", help="Handle one native host hook event")
    hook.add_argument("host", choices=["codex", "claude"], help="Native hook protocol")
    hook.add_argument("--db", default=None, help="SQLite database path")
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
        _bind(action_parser, handlers, "cmd_dashboard_service")
    install = service_sub.add_parser(
        "install", help="Register and start the current-user dashboard service"
    )
    install.add_argument(
        "--dry-run", action="store_true", help="Print the service plan without changing the host"
    )
    install.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(install, handlers, "cmd_dashboard_service")
    open_p = service_sub.add_parser("open", help="Resolve and open the live authenticated URL")
    open_p.add_argument(
        "--no-open", action="store_true", help="Print status without launching a browser"
    )
    open_p.add_argument("--json", action="store_true", help="Print machine-readable results")
    _bind(open_p, handlers, "cmd_dashboard_service")


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


def _register_passthrough_commands(sub: Subparsers, handlers: Handlers) -> None:
    codex = sub.add_parser("codex", help="Codex adapter commands")
    codex_sub = codex.add_subparsers(dest="codex_command", required=True)
    codex_exec = codex_sub.add_parser("exec", help="Run codex exec")
    codex_exec.add_argument("args", nargs=argparse.REMAINDER, help="Arguments passed to codex exec")
    _bind(codex_exec, handlers, "cmd_codex_exec")

    run = sub.add_parser("run", help="Run an arbitrary command")
    run.add_argument("args", nargs=argparse.REMAINDER, help="Command and arguments to execute")
    _bind(run, handlers, "cmd_run")


def build_parser(handlers: Handlers) -> argparse.ArgumentParser:
    """Build the command tree with callbacks supplied by the public facade."""
    parser = argparse.ArgumentParser(prog="agency", description="Agency Runtime Control Plane")
    sub = parser.add_subparsers(dest="command", required=True)
    _register_install(sub, handlers)
    _register_host_control(sub, handlers)
    _register_configuration(sub, handlers)
    _register_roster(sub, handlers)
    _register_selection(sub, handlers)
    _register_delegation_and_evals(sub, handlers)
    _register_database(sub, handlers)
    _register_native_protocols(sub, handlers)
    _register_services(sub, handlers)
    _register_passthrough_commands(sub, handlers)
    return parser
