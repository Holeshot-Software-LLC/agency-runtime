"""Bounded, redacted Codex hook-trust inspection."""

from __future__ import annotations

import json
import queue
import sys
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import launcher_bootstrap
from agency_runtime.core.codex_hook_trust import (
    _AGENCY_CODEX_PLUGIN_ID,
    _await_response,
    _project_hooks_response,
    _run_worker,
    _trusted_worker_argv,
    inspect_codex_hook_trust,
    sanitize_codex_hook_trust_report,
)
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.installer_contracts import CODEX_HOOK_EVENTS
from agency_runtime.core.process_argv import (
    absolute_executable_path,
    agency_bootstrap_path,
    isolated_python_argv,
)


def _events() -> tuple[str, ...]:
    return tuple(event[0].lower() + event[1:] for event in CODEX_HOOK_EVENTS)


def _hook(
    event: str,
    *,
    enabled: bool = True,
    trust: str = "trusted",
    current_hash: str = "sha256:" + "a" * 64,
) -> dict[str, object]:
    return {
        "command": "SECRET_COMMAND --token SECRET_TOKEN",
        "currentHash": current_hash,
        "enabled": enabled,
        "eventName": event,
        "handlerType": "command",
        "isManaged": False,
        "matcher": "SECRET_MATCHER",
        "pluginId": _AGENCY_CODEX_PLUGIN_ID,
        "source": "plugin",
        "sourcePath": "C:/SECRET/source/path",
        "trustStatus": trust,
    }


def _response(
    cwd: Path,
    hooks: list[object],
    *,
    warnings: list[object] | None = None,
    errors: list[object] | None = None,
) -> dict[str, object]:
    return {
        "data": [
            {
                "cwd": str(cwd),
                "hooks": hooks,
                "warnings": [] if warnings is None else warnings,
                "errors": [] if errors is None else errors,
            }
        ]
    }


def _project(cwd: Path, hooks: list[object], **kwargs: object) -> dict[str, object]:
    return _project_hooks_response(
        _response(cwd, hooks, **kwargs),
        cwd=str(cwd),
        expected_events=_events(),
        plugin_id=_AGENCY_CODEX_PLUGIN_ID,
    )


def _trusted_report() -> dict[str, object]:
    cwd = Path.cwd()
    return _project(cwd, [_hook(event) for event in _events()])


def test_projection_requires_exact_trusted_inventory_and_redacts_commands(tmp_path: Path) -> None:
    hooks: list[object] = [
        {**_hook("stop"), "pluginId": "unrelated@plugin"},
        *[_hook(event) for event in _events()],
    ]

    report = _project(tmp_path, hooks)

    assert report["status"] == "trusted"
    assert report["expected_count"] == report["observed_count"] == 8
    assert report["trusted_count"] == 8
    assert tuple(report["events"]) == _events()
    encoded = json.dumps(report)
    assert "SECRET" not in encoded
    assert "command" not in encoded
    assert "sourcePath" not in encoded
    assert "matcher" not in encoded


@pytest.mark.parametrize(
    ("changes", "expected_status", "count_field"),
    [
        ({"trust": "modified"}, "modified", "modified_count"),
        ({"trust": "untrusted"}, "untrusted", "untrusted_count"),
        ({"enabled": False}, "disabled", "disabled_count"),
    ],
)
def test_projection_fails_closed_for_each_unready_state(
    tmp_path: Path,
    changes: dict[str, object],
    expected_status: str,
    count_field: str,
) -> None:
    hooks = [_hook(event, **changes) for event in _events()]

    report = _project(tmp_path, hooks)

    assert report["status"] == expected_status
    assert report[count_field] == 8


def test_projection_reports_missing_duplicate_unexpected_and_managed(tmp_path: Path) -> None:
    expected = _events()
    missing = _project(tmp_path, [_hook(event) for event in expected[:-1]])
    duplicate = _project(tmp_path, [*[_hook(event) for event in expected], _hook(expected[0])])
    unexpected = _project(tmp_path, [*[_hook(event) for event in expected], _hook("preCompact")])
    managed = _project(tmp_path, [_hook(event, trust="managed") for event in expected])

    assert missing["status"] == "missing"
    assert missing["missing_count"] == 1
    assert duplicate["status"] == "error"
    assert duplicate["duplicate_count"] == 1
    assert unexpected["status"] == "error"
    assert unexpected["unexpected_count"] == 1
    assert managed["status"] == "error"
    assert managed["managed_count"] == 8


@pytest.mark.parametrize(
    "mutator",
    [
        lambda hooks: hooks[0].update(currentHash="sha256:not-a-hash"),
        lambda hooks: hooks[0].update(enabled=1),
        lambda hooks: hooks[0].update(handlerType="prompt"),
        lambda hooks: hooks[0].update(source="user"),
        lambda hooks: hooks[0].update(pluginId=42),
        lambda hooks: hooks[0].update(isManaged=True),
    ],
)
def test_projection_rejects_malformed_selected_metadata(
    tmp_path: Path,
    mutator,
) -> None:
    hooks = [_hook(event) for event in _events()]
    mutator(hooks)

    report = _project(tmp_path, hooks)

    assert report["status"] == "error"
    assert report["error"] == "hook_metadata_invalid"


def test_projection_rejects_scope_warnings_errors_and_cwd_mismatch(tmp_path: Path) -> None:
    hooks = [_hook(event) for event in _events()]
    warned = _project_hooks_response(
        _response(tmp_path, hooks, warnings=["SECRET_WARNING"]),
        cwd=str(tmp_path),
        expected_events=_events(),
        plugin_id=_AGENCY_CODEX_PLUGIN_ID,
    )
    errored = _project_hooks_response(
        _response(tmp_path, hooks, errors=[{"message": "SECRET_ERROR"}]),
        cwd=str(tmp_path),
        expected_events=_events(),
        plugin_id=_AGENCY_CODEX_PLUGIN_ID,
    )
    mismatched = _project_hooks_response(
        _response(tmp_path, hooks),
        cwd=str(tmp_path / "other"),
        expected_events=_events(),
        plugin_id=_AGENCY_CODEX_PLUGIN_ID,
    )

    assert warned["status"] == "error"
    assert warned["warning_count"] == 1
    assert "SECRET" not in json.dumps(warned)
    assert errored["status"] == "error"
    assert errored["error_count"] == 1
    assert "SECRET" not in json.dumps(errored)
    assert mismatched["error"] == "cwd_mismatch"


def test_sanitizer_rejects_forged_or_extended_trusted_reports() -> None:
    forged = _trusted_report()
    forged["events"] = {}
    forged["missing_count"] = 0
    extended = _trusted_report()
    extended["command"] = "SECRET_COMMAND"

    assert sanitize_codex_hook_trust_report(forged)["status"] == "error"
    sanitized = sanitize_codex_hook_trust_report(extended)
    assert sanitized["status"] == "error"
    assert "SECRET" not in json.dumps(sanitized)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda report: report.update(status=[]),
        lambda report: report.update(status="error", error={}),
        lambda report: next(iter(report["events"].values())).update(trustStatus=[]),
    ],
)
def test_sanitizer_fails_closed_on_unhashable_protocol_values(mutation) -> None:
    report = _trusted_report()
    mutation(report)

    sanitized = sanitize_codex_hook_trust_report(report)

    assert sanitized["status"] == "error"
    assert sanitized["error"] == "inspection_output_invalid"


@pytest.mark.parametrize("response_id", [True, 2, "1"])
def test_protocol_rejects_ambiguous_or_unexpected_response_ids(response_id: object) -> None:
    messages: queue.Queue[tuple[str, bytes]] = queue.Queue()
    messages.put(("line", json.dumps({"id": response_id, "result": {}}).encode("utf-8")))

    with pytest.raises(ValueError, match="response id"):
        _await_response(messages, request_id=1, deadline=time.monotonic() + 1)


@pytest.mark.parametrize(
    ("result", "error"),
    [
        (BoundedProcessResult(124, "", "SECRET", timed_out=True), "inspection_timed_out"),
        (BoundedProcessResult(1, "", "SECRET"), "inspection_failed"),
        (
            BoundedProcessResult(0, "{}", "SECRET", stdout_truncated=True),
            "inspection_output_truncated",
        ),
        (BoundedProcessResult(0, "not-json", "SECRET"), "inspection_output_invalid"),
    ],
)
def test_public_inspector_fails_closed_without_leaking_process_output(
    tmp_path: Path,
    result: BoundedProcessResult,
    error: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.process_argv.freeze_persistent_process_argv",
        lambda argv: argv,
    )
    report = inspect_codex_hook_trust(
        tmp_path,
        executable="codex",
        runner=lambda *_args, **_kwargs: result,
    )

    assert report["status"] == "error"
    assert report["error"] == error
    assert "SECRET" not in json.dumps(report)


def test_public_inspector_accepts_only_a_consistent_worker_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = _trusted_report()
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        "agency_runtime.core.process_argv.freeze_persistent_process_argv",
        lambda argv: argv,
    )

    def runner(*_args: object, **kwargs: object) -> BoundedProcessResult:
        calls.append(kwargs)
        return BoundedProcessResult(0, json.dumps(expected), "SECRET_STDERR")

    report = inspect_codex_hook_trust(tmp_path, executable="codex", runner=runner)

    assert report == expected
    assert calls[0]["input_text"]
    assert calls[0]["max_input_bytes"] == 16 * 1024
    assert "SECRET" not in json.dumps(report)


def test_interactive_worker_completes_initialize_and_hooks_list(tmp_path: Path) -> None:
    fake_server = tmp_path / "app-server"
    expected = list(_events())
    fake_server.write_text(
        "\n".join(
            [
                "import json, sys",
                f"events = {expected!r}",
                "for line in sys.stdin.buffer:",
                "    request = json.loads(line)",
                "    if request.get('method') == 'initialize':",
                "        print(json.dumps({'id': 1, 'result': {'server': 'fake'}}), flush=True)",
                "    elif request.get('method') == 'hooks/list':",
                "        cwd = request['params']['cwds'][0]",
                "        hooks = []",
                "        for event in events:",
                "            hooks.append({'pluginId': 'agency-preflight@agency-runtime',",
                "                'eventName': event, 'enabled': True, 'trustStatus': 'trusted',",
                "                'currentHash': 'sha256:' + 'b' * 64, 'source': 'plugin',",
                "                'handlerType': 'command', 'isManaged': False,",
                "                'command': 'SECRET_COMMAND', 'sourcePath': 'SECRET_PATH'})",
                "        result = {'data': [{'cwd': cwd, 'hooks': hooks,",
                "            'warnings': [], 'errors': []}]}",
                "        print(json.dumps({'id': 2, 'result': result}), flush=True)",
            ]
        ),
        encoding="utf-8",
    )

    report = _run_worker(
        {
            "executable": sys._base_executable,
            "cwd": str(tmp_path),
            "expected_events": expected,
            "plugin_id": _AGENCY_CODEX_PLUGIN_ID,
            "timeout": 10,
        }
    )

    assert report["status"] == "trusted"
    assert report["trusted_count"] == 8
    assert "SECRET" not in json.dumps(report)


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), True, 31])
def test_inspector_rejects_unbounded_timeouts(tmp_path: Path, timeout: object) -> None:
    with pytest.raises(ValueError, match="timeout"):
        inspect_codex_hook_trust(tmp_path, timeout=timeout)  # type: ignore[arg-type]


def test_worker_argv_launches_the_published_projection_not_the_checkout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A checkout-run CLI must not build its worker from checkout artifacts.

    Both the virtual environment's interpreter and the checkout's own
    ``_bootstrap.py`` are cross-account writable, so an argv naming either can
    never be frozen. Regressing this makes every inspection fail while Codex
    itself is healthy.
    """

    published = tmp_path / "launchers" / "runtime-sha256-abc" / "site-packages"
    bootstrap = published / "agency_runtime" / "_bootstrap.py"
    bootstrap.parent.mkdir(parents=True)
    bootstrap.write_text("# published", encoding="utf-8")

    plan = SimpleNamespace(bootstrap_path=str(bootstrap))
    monkeypatch.setattr(launcher_bootstrap, "running_runtime_digest", lambda: "")
    monkeypatch.setattr(launcher_bootstrap, "plan_private_package_runtime", lambda _: plan)
    monkeypatch.setattr(launcher_bootstrap, "verify_private_package_runtime", lambda _: "abc")
    monkeypatch.setattr(
        launcher_bootstrap, "persistent_python_executable", lambda: sys._base_executable
    )

    argv = _trusted_worker_argv()

    assert argv[3] == str(bootstrap)
    assert argv[3] != agency_bootstrap_path()
    assert argv[0] == absolute_executable_path(sys._base_executable)
    assert argv[1:3] == ["-I", "-S"]
    assert argv[4:] == ["agency_runtime.core.codex_hook_trust", "--worker"]


def test_absent_projection_is_not_reported_as_a_trust_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unlaunchable inspector must never read as `the hooks are untrusted`.

    `inspection_failed` with `observed=0 missing=8` was indistinguishable from
    a real negative and cost a full measurement attempt.
    """

    def _unavailable(_: object) -> str:
        raise FileNotFoundError("persistent executable artifact is unavailable")

    monkeypatch.setattr(launcher_bootstrap, "running_runtime_digest", lambda: "")
    monkeypatch.setattr(launcher_bootstrap, "verify_private_package_runtime", _unavailable)

    report = inspect_codex_hook_trust(tmp_path, timeout=5.0)

    assert report["error"] == "worker_projection_unavailable"
    assert report["error"] != "inspection_failed"
    assert report["status"] == "error"
    assert report["observed_count"] == 0
    assert sanitize_codex_hook_trust_report(report)["error"] == "worker_projection_unavailable"


def test_isolated_python_argv_bootstrap_override_is_opt_in() -> None:
    default = isolated_python_argv(sys._base_executable, "agency_runtime.cli")
    overridden = isolated_python_argv(
        sys._base_executable, "agency_runtime.cli", bootstrap_path="C:/published/_bootstrap.py"
    )

    assert default[3] == agency_bootstrap_path()
    assert overridden[3] == str(Path("C:/published/_bootstrap.py"))
    assert default[:3] == overridden[:3]
