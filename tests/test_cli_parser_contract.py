"""Golden contracts for the complete declarative CLI parser surface."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Iterator
from typing import Any

import pytest

from agency_runtime import __version__
from agency_runtime.cli import parser as parser_module

HANDLER_NAMES = (
    "cmd_agent_disable",
    "cmd_agent_enable",
    "cmd_agents_list",
    "cmd_codex_exec",
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
    "cmd_delegate",
    "cmd_doctor",
    "cmd_eval_compare",
    "cmd_eval_decision_conformance",
    "cmd_eval_delegation",
    "cmd_eval_full_roster",
    "cmd_eval_product",
    "cmd_eval_routing",
    "cmd_eval_upstream_architecture",
    "cmd_eval_upstream_selection",
    "cmd_eval_workforce",
    "cmd_explain",
    "cmd_hook",
    "cmd_host_canary",
    "cmd_hiring_approve",
    "cmd_hiring_list",
    "cmd_hiring_show",
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
    "cmd_run",
    "cmd_search",
    "cmd_serve",
    "cmd_smoke",
    "cmd_source_add",
    "cmd_source_list",
    "cmd_status",
    "cmd_sync",
    "cmd_upgrade",
    "cmd_version",
    "cmd_workforce_consolidate",
    "cmd_workforce_duplicates",
    "cmd_workforce_list",
    "cmd_workforce_search",
    "cmd_workforce_show",
    "cmd_workforce_transition",
)
EXPECTED_PATHS = (
    "agency",
    "agency agents",
    "agency agents disable",
    "agency agents enable",
    "agency agents list",
    "agency codex",
    "agency codex exec",
    "agency config",
    "agency config get",
    "agency config path",
    "agency config provider",
    "agency config provider list",
    "agency config provider models",
    "agency config provider remove",
    "agency config provider set",
    "agency config reset",
    "agency config set",
    "agency config show",
    "agency config validate",
    "agency configure",
    "agency contractor",
    "agency contractor list",
    "agency contractor show",
    "agency dashboard",
    "agency dashboard service",
    "agency dashboard service install",
    "agency dashboard service open",
    "agency dashboard service restart",
    "agency dashboard service start",
    "agency dashboard service status",
    "agency dashboard service stop",
    "agency dashboard service uninstall",
    "agency db",
    "agency db stats",
    "agency db trim",
    "agency delegate",
    "agency doctor",
    "agency eval",
    "agency eval compare",
    "agency eval decision-conformance",
    "agency eval delegation",
    "agency eval full-roster",
    "agency eval product",
    "agency eval routing",
    "agency eval upstream-architecture",
    "agency eval upstream-selection",
    "agency eval workforce",
    "agency explain",
    "agency hiring",
    "agency hiring approve",
    "agency hiring list",
    "agency hiring show",
    "agency hook",
    "agency host-canary",
    "agency install",
    "agency mcp",
    "agency off",
    "agency on",
    "agency policy",
    "agency roster",
    "agency roster activate",
    "agency roster approve",
    "agency roster candidate",
    "agency roster candidate audit",
    "agency roster candidate compare",
    "agency roster candidate findings",
    "agency roster candidate reject",
    "agency roster diff",
    "agency roster list",
    "agency roster remediation",
    "agency roster remediation queue",
    "agency roster retire",
    "agency roster rollback",
    "agency roster scans",
    "agency roster upstream",
    "agency roster upstream import",
    "agency roster upstream status",
    "agency route",
    "agency run",
    "agency search",
    "agency serve",
    "agency smoke",
    "agency source",
    "agency source add",
    "agency source list",
    "agency status",
    "agency sync",
    "agency uninstall",
    "agency upgrade",
    "agency version",
    "agency workforce",
    "agency workforce amend",
    "agency workforce consolidate",
    "agency workforce disable",
    "agency workforce duplicates",
    "agency workforce enable",
    "agency workforce list",
    "agency workforce merge",
    "agency workforce promote",
    "agency workforce resume",
    "agency workforce retire",
    "agency workforce search",
    "agency workforce show",
    "agency workforce suspend",
)
EXPECTED_BINDINGS = {
    "agency agents disable": "cmd_agent_disable",
    "agency agents enable": "cmd_agent_enable",
    "agency agents list": "cmd_agents_list",
    "agency codex exec": "cmd_codex_exec",
    "agency config get": "cmd_config_get",
    "agency config path": "cmd_config_path",
    "agency config provider list": "cmd_config_provider_list",
    "agency config provider models": "cmd_config_provider_models",
    "agency config provider remove": "cmd_config_provider_remove",
    "agency config provider set": "cmd_config_provider_set",
    "agency config reset": "cmd_config_reset",
    "agency config set": "cmd_config_set",
    "agency config show": "cmd_config_show",
    "agency config validate": "cmd_config_validate",
    "agency configure": "cmd_configure",
    "agency contractor list": "cmd_contractor_list",
    "agency contractor show": "cmd_workforce_show",
    "agency dashboard": "cmd_dashboard",
    "agency dashboard service install": "cmd_dashboard_service",
    "agency dashboard service open": "cmd_dashboard_service",
    "agency dashboard service restart": "cmd_dashboard_service",
    "agency dashboard service start": "cmd_dashboard_service",
    "agency dashboard service status": "cmd_dashboard_service",
    "agency dashboard service stop": "cmd_dashboard_service",
    "agency dashboard service uninstall": "cmd_dashboard_service",
    "agency db stats": "cmd_db_stats",
    "agency db trim": "cmd_db_trim",
    "agency delegate": "cmd_delegate",
    "agency doctor": "cmd_doctor",
    "agency eval compare": "cmd_eval_compare",
    "agency eval decision-conformance": "cmd_eval_decision_conformance",
    "agency eval delegation": "cmd_eval_delegation",
    "agency eval full-roster": "cmd_eval_full_roster",
    "agency eval product": "cmd_eval_product",
    "agency eval routing": "cmd_eval_routing",
    "agency eval upstream-architecture": "cmd_eval_upstream_architecture",
    "agency eval upstream-selection": "cmd_eval_upstream_selection",
    "agency eval workforce": "cmd_eval_workforce",
    "agency explain": "cmd_explain",
    "agency hook": "cmd_hook",
    "agency host-canary": "cmd_host_canary",
    "agency hiring approve": "cmd_hiring_approve",
    "agency hiring list": "cmd_hiring_list",
    "agency hiring show": "cmd_hiring_show",
    "agency install": "cmd_install",
    "agency uninstall": "cmd_uninstall",
    "agency mcp": "cmd_mcp",
    "agency off": "cmd_off",
    "agency on": "cmd_on",
    "agency policy": "cmd_policy",
    "agency roster activate": "cmd_roster_activate",
    "agency roster approve": "cmd_roster_approve",
    "agency roster candidate audit": "cmd_roster_candidate_audit",
    "agency roster candidate compare": "cmd_roster_candidate_compare",
    "agency roster candidate findings": "cmd_roster_candidate_findings",
    "agency roster candidate reject": "cmd_roster_candidate_reject",
    "agency roster diff": "cmd_roster_diff",
    "agency roster list": "cmd_roster_list",
    "agency roster remediation queue": "cmd_roster_remediation_queue",
    "agency roster retire": "cmd_roster_retire",
    "agency roster rollback": "cmd_roster_rollback",
    "agency roster scans": "cmd_roster_scans",
    "agency roster upstream import": "cmd_roster_upstream_import",
    "agency roster upstream status": "cmd_roster_upstream_status",
    "agency route": "cmd_route",
    "agency run": "cmd_run",
    "agency search": "cmd_search",
    "agency serve": "cmd_serve",
    "agency smoke": "cmd_smoke",
    "agency source add": "cmd_source_add",
    "agency source list": "cmd_source_list",
    "agency status": "cmd_status",
    "agency sync": "cmd_sync",
    "agency upgrade": "cmd_upgrade",
    "agency version": "cmd_version",
    "agency workforce disable": "cmd_agent_disable",
    "agency workforce amend": "cmd_hiring_approve",
    "agency workforce consolidate": "cmd_workforce_consolidate",
    "agency workforce duplicates": "cmd_workforce_duplicates",
    "agency workforce enable": "cmd_agent_enable",
    "agency workforce list": "cmd_workforce_list",
    "agency workforce merge": "cmd_workforce_transition",
    "agency workforce promote": "cmd_workforce_transition",
    "agency workforce resume": "cmd_workforce_transition",
    "agency workforce retire": "cmd_workforce_transition",
    "agency workforce search": "cmd_workforce_search",
    "agency workforce show": "cmd_workforce_show",
    "agency workforce suspend": "cmd_workforce_transition",
}
EXPECTED_MANIFEST_SHA256 = "63138490f7877dc7fe85783dcf47fe29b3a1c3dfeeeca2c3c101eb34d983fd6b"


def _handler(name: str):
    def command(_args: argparse.Namespace) -> int:
        return 0

    command.__name__ = name
    return command


def _parser() -> argparse.ArgumentParser:
    return parser_module.build_parser({name: _handler(name) for name in HANDLER_NAMES})


def _scalar(value: Any) -> Any:
    if callable(value):
        return getattr(value, "__name__", type(value).__name__)
    if value is argparse.SUPPRESS:
        return "SUPPRESS"
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_scalar(item) for item in value]
    return str(value)


def _walk_parser(
    parser: argparse.ArgumentParser,
    path: str = "agency",
) -> Iterator[tuple[str, argparse.ArgumentParser]]:
    yield path, parser
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, child in sorted(action.choices.items()):
            yield from _walk_parser(child, f"{path} {name}")


def _action_contract(action: argparse.Action) -> dict[str, Any]:
    choices = (
        sorted(action.choices)
        if isinstance(action, argparse._SubParsersAction)
        else list(action.choices)
        if action.choices is not None
        else None
    )
    return {
        "class": type(action).__name__,
        "options": list(action.option_strings),
        "dest": action.dest,
        "nargs": _scalar(action.nargs),
        "const": _scalar(action.const),
        "default": _scalar(action.default),
        "type": _scalar(action.type),
        "choices": choices,
        # CPython 3.12 and 3.13 disagree on the internal ``required`` flag for
        # REMAINDER positionals even though both accept an empty remainder.
        # Canonicalize the observable contract instead of hashing that private
        # implementation detail into a supposedly cross-platform golden file.
        "required": False if action.nargs == argparse.REMAINDER else action.required,
        "help": _scalar(action.help),
        "metavar": _scalar(action.metavar),
    }


def _parser_contract(path: str, parser: argparse.ArgumentParser) -> dict[str, Any]:
    return {
        "path": path,
        "prog": parser.prog,
        "description": parser.description,
        "epilog": parser.epilog,
        "defaults": {key: _scalar(value) for key, value in sorted(parser._defaults.items())},
        "actions": [_action_contract(action) for action in parser._actions],
        "mutex": [
            {
                "required": group.required,
                "members": [action.dest for action in group._group_actions],
            }
            for group in parser._mutually_exclusive_groups
        ],
    }


def test_complete_cli_parser_manifest_matches_golden_contract() -> None:
    tree = list(_walk_parser(_parser()))
    manifest = [_parser_contract(path, parser) for path, parser in tree]
    payload = json.dumps(
        manifest,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode()

    assert tuple(path for path, _parser in tree) == EXPECTED_PATHS
    assert hashlib.sha256(payload, usedforsecurity=False).hexdigest() == EXPECTED_MANIFEST_SHA256


def test_global_version_reports_the_canonical_package_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        _parser().parse_args(["--version"])

    assert raised.value.code == 0
    assert capsys.readouterr().out == f"agency {__version__}\n"


def test_remediation_queue_parser_exposes_independent_cursor_paging() -> None:
    parsed = _parser().parse_args(
        [
            "roster",
            "remediation",
            "queue",
            "--limit",
            "17",
            "--pending-cursor",
            "pending-event",
            "--history-cursor",
            "history-event",
        ]
    )

    assert parsed.limit == 17
    assert parsed.pending_cursor == "pending-event"
    assert parsed.history_cursor == "history-event"
    assert parsed.func.__name__ == "cmd_roster_remediation_queue"


@pytest.mark.parametrize(
    "event",
    ["PreToolUse", "SubagentStart", "SubagentStop"],
)
def test_claude_native_child_hook_events_reach_the_installer_bound_handler(
    event: str,
) -> None:
    parsed = _parser().parse_args(["hook", "claude", "--event", event])

    assert parsed.event == event
    assert parsed.func.__name__ == "cmd_hook"


def test_every_public_cli_argument_explains_itself() -> None:
    missing: list[str] = []
    for path, parser in _walk_parser(_parser()):
        for action in parser._actions:
            if isinstance(action, (argparse._HelpAction, argparse._SubParsersAction)):
                continue
            if action.help is argparse.SUPPRESS:
                continue
            if not isinstance(action.help, str) or not action.help.strip():
                label = ", ".join(action.option_strings) or action.dest
                missing.append(f"{path}: {label}")

    assert missing == []


def test_every_command_parser_retains_its_facade_handler_binding() -> None:
    bindings = {
        path: parser._defaults["func"].__name__
        for path, parser in _walk_parser(_parser())
        if "func" in parser._defaults
    }

    assert bindings == EXPECTED_BINDINGS


def test_install_parser_exposes_explicit_autonomous_activation_mode() -> None:
    parsed = _parser().parse_args(["install", "--autonomous", "--verify-activation", "--json"])

    assert parsed.autonomous is True
    assert parsed.verify_activation is True
    assert parsed.agent is None
    assert parsed.json is True


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            ["install"],
            {
                "command": "install",
                "profile": None,
                "all": False,
                "agent": None,
                "autonomous": False,
                "dry_run": False,
                "rollback": False,
                "backup": None,
                "no_dashboard": False,
                "verify_activation": False,
                "activation_timeout": 180.0,
                "json": False,
                "func": "cmd_install",
            },
        ),
        (
            ["config", "set", "judge.model", "--stdin"],
            {
                "command": "config",
                "config_command": "set",
                "key": "judge.model",
                "value": None,
                "stdin": True,
                "prompt": False,
                "clear": False,
                "func": "cmd_config_set",
            },
        ),
        (
            ["delegate", "--task", "x", "--command", "tool", "--flag"],
            {
                "command": ["tool", "--flag"],
                "backend": "generic",
                "agent": "",
                "task": "x",
                "workdir": None,
                "timeout": None,
                "json": False,
                "func": "cmd_delegate",
            },
        ),
        (
            ["dashboard", "service", "install"],
            {
                "command": "dashboard",
                "port": 0,
                "db": None,
                "no_open": False,
                "service_mode": False,
                "config": None,
                "dashboard_command": "service",
                "dashboard_service_action": "install",
                "dry_run": False,
                "json": False,
                "func": "cmd_dashboard_service",
            },
        ),
        (
            ["codex", "exec", "--", "--help"],
            {
                "command": "codex",
                "codex_command": "exec",
                "args": ["--", "--help"],
                "func": "cmd_codex_exec",
            },
        ),
    ],
)
def test_nested_and_remainder_parsing_contracts(argv: list[str], expected: dict[str, Any]) -> None:
    parsed = vars(_parser().parse_args(argv))
    parsed["func"] = parsed["func"].__name__

    assert parsed == expected


@pytest.mark.parametrize(("value", "expected"), [("1", 1), ("17", 17)])
def test_positive_integer_parser_accepts_supported_values(value: str, expected: int) -> None:
    assert parser_module._positive_int(value) == expected


@pytest.mark.parametrize("value", ["", "0", "-1", "not-an-integer"])
def test_positive_integer_parser_rejects_invalid_values(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="must be a positive integer"):
        parser_module._positive_int(value)


@pytest.mark.parametrize(("value", "expected"), [("1", 1), ("100", 100)])
def test_search_limit_accepts_bounded_values(value: str, expected: int) -> None:
    assert parser_module._search_limit(value) == expected


def test_search_limit_rejects_values_above_the_wire_contract() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="1 through 100"):
        parser_module._search_limit("101")
