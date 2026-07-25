"""Restricted-Windows CLI brokerage through the authenticated dashboard."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.cli import install_commands
from agency_runtime.core import dashboard_runtime
from agency_runtime.core.host_control import SUPPORTED_HOSTS
from agency_runtime.core.windows_acl import RestrictedWindowsTokenError


def _master(enabled: bool = True, *, generation: int = 3) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "enabled": enabled,
        "generation": generation,
        "updated_at": "2026-07-16T12:00:00Z",
        "source": "dashboard",
    }


def _status(
    host: str,
    *,
    enabled: bool = True,
    master_enabled: bool = True,
    generation: int = 2,
) -> dict[str, Any]:
    return {
        "host": host,
        "runtime_enabled": enabled,
        "master_enabled": master_enabled,
        "effective_enabled": enabled and master_enabled,
        "runtime_control_generation": generation,
        "runtime_control_updated_at": "2026-07-16T12:00:00Z",
        "runtime_control_source": "dashboard",
    }


def _identity() -> dict[str, Any]:
    config_path = str(Path(install_commands.resolve_config_path()).resolve())
    store_path = str((Path.cwd() / "agency.db").resolve())
    return {
        "config_path": config_path,
        "config_revision": "sha256:" + ("a" * 64),
        "environment_overrides": {},
        "store_path": store_path,
        "desired_store_path": store_path,
        "store_restart_required": False,
    }


def _snapshot(*, enabled: bool = True) -> dict[str, Any]:
    return {
        "hosts": [_status(host, master_enabled=enabled) for host in SUPPORTED_HOSTS],
        "master": _master(enabled),
        **_identity(),
    }


def _inference() -> dict[str, Any]:
    return {
        "schema_version": "agency.dashboard.inference_operations.v1",
        "configured": False,
        "required_for_eligible_turns": False,
        "state": "not_configured",
        "evidence": "configuration readiness plus recent persisted routing/model receipts",
        "provider_chain": [],
        "latest_model_resolution": None,
        "recent_failures": [],
        "failure_count": 0,
        "failures_truncated": False,
    }


def _broker_identity() -> Any:
    return install_commands._broker_store_identity(_identity())


def _args(**overrides: Any) -> Namespace:
    values = {
        "agent": "codex",
        "dry_run": False,
        "global_control": False,
        "json": True,
        "native": False,
    }
    values.update(overrides)
    return Namespace(**values)


def _restricted_store(_config: Any) -> Any:
    raise RestrictedWindowsTokenError("restricted process token")


def test_dashboard_control_endpoints_require_exact_method_pairs() -> None:
    with pytest.raises(ValueError, match="requires POST"):
        dashboard_runtime.dashboard_api_request("/api/hosts/toggle")
    with pytest.raises(ValueError, match="requires GET"):
        dashboard_runtime.dashboard_api_request("/api/hosts", method="POST", payload={})
    with pytest.raises(ValueError, match="requires GET"):
        dashboard_runtime.dashboard_api_request("/api/inference", method="POST", payload={})


@pytest.mark.parametrize("value", [True, None, "2", -1])
def test_broker_generation_rejects_non_integer_or_negative_values(value: Any) -> None:
    with pytest.raises(ValueError, match="invalid generation"):
        install_commands._broker_generation({"generation": value}, "generation")


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([], "JSON object"),
        ({}, "identity"),
        ({**_status("codex"), "host": "attacker"}, "identity"),
        ({**_status("codex"), "runtime_enabled": 1}, "JSON booleans"),
        ({**_status("codex"), "master_enabled": "yes"}, "JSON booleans"),
        ({**_status("codex"), "effective_enabled": 1}, "boolean or null"),
        (
            {**_status("codex", enabled=False), "effective_enabled": True},
            "internally inconsistent",
        ),
        ({**_status("codex"), "runtime_control_generation": True}, "invalid"),
    ],
)
def test_broker_host_status_rejects_malformed_control_fields(
    value: Any,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        install_commands._broker_host_status(value, expected_host="codex")


def test_dashboard_host_snapshot_returns_canonical_order_and_selected_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(dashboard_runtime, "dashboard_api_request", lambda _path: _snapshot())

    all_hosts, master = install_commands._dashboard_host_snapshot(None)
    selected, selected_master = install_commands._dashboard_host_snapshot("codex")

    assert [item["host"] for item in all_hosts] == list(SUPPORTED_HOSTS)
    assert selected == [_status("codex")]
    assert selected_master == master == _master()


def test_dashboard_inference_snapshot_is_identity_bound_and_redacted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = {
        **_identity(),
        **_inference(),
        "api_key": "must-not-cross",
        "prompt_body": "must-not-cross",
    }
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda path: response if path == "/api/inference" else {},
    )

    inference, identity = install_commands._dashboard_inference_snapshot_with_identity()

    assert inference == _inference()
    assert identity == _broker_identity()
    assert "must-not-cross" not in repr(inference)


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"hosts": {}, "master": _master()}, "every supported host"),
        ({"hosts": [_status("codex")], "master": _master()}, "every supported host"),
        (
            {
                "hosts": [None, *[_status(host) for host in SUPPORTED_HOSTS[1:]]],
                "master": _master(),
            },
            "invalid entry",
        ),
        (
            {
                "hosts": [
                    _status("hermes"),
                    _status("codex"),
                    _status("codex"),
                    _status("openclaw"),
                    _status("claude"),
                ],
                "master": _master(),
            },
            "duplicate host",
        ),
        (
            {
                "hosts": [
                    _status("hermes", master_enabled=False),
                    *[_status(host) for host in SUPPORTED_HOSTS[1:]],
                ],
                "master": _master(),
            },
            "disagrees",
        ),
    ],
)
def test_dashboard_host_snapshot_rejects_incomplete_or_inconsistent_payloads(
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, Any],
    message: str,
) -> None:
    response = {**_identity(), **payload}
    monkeypatch.setattr(dashboard_runtime, "dashboard_api_request", lambda _path: response)
    with pytest.raises(ValueError, match=message):
        install_commands._dashboard_host_snapshot(None)


def test_dashboard_soft_control_supports_dry_run_and_generation_checked_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[tuple[str, str, Any]] = []

    def request(path: str, *, method: str = "GET", payload: Any = None) -> dict[str, Any]:
        requests.append((path, method, payload))
        if path == "/api/hosts":
            return _snapshot()
        return {
            "ok": True,
            "host": "codex",
            "enabled": False,
            "generation": 3,
            "updated_at": "after",
            "source": "dashboard",
            "status": {
                **_status("codex", enabled=False, generation=3),
                "runtime_control_updated_at": "after",
            },
            **_identity(),
        }

    monkeypatch.setattr(dashboard_runtime, "dashboard_api_request", request)

    dry_run = install_commands._dashboard_soft_control_result("codex", enabled=False, dry_run=True)
    changed = install_commands._dashboard_soft_control_result("codex", enabled=False, dry_run=False)

    assert dry_run["dry_run"] is True
    assert dry_run["runtime_enabled"] is False
    assert changed["generation"] == 3
    assert changed["previous_generation"] == 2
    assert changed["transport"] == "dashboard"
    assert requests[-1] == (
        "/api/hosts/toggle",
        "POST",
        {
            "host": "codex",
            "enabled": False,
            "expected_generation": 2,
            "confirm": "DISABLE codex",
        },
    )


@pytest.mark.parametrize(
    ("toggle", "message"),
    [
        ({"ok": False, "host": "codex"}, "identity"),
        ({"ok": True, "host": "claude"}, "identity"),
        ({"ok": True, "host": "codex", "enabled": 0}, "state"),
        ({"ok": True, "host": "codex", "enabled": True}, "state"),
        ({"ok": True, "host": "codex", "enabled": False, "generation": True}, "invalid"),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 3,
                "status": _status("claude", enabled=False, generation=3),
            },
            "identity",
        ),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 3,
                "status": _status("codex", enabled=True, generation=3),
            },
            "inconsistent",
        ),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 2,
                "status": _status("codex", enabled=False, generation=2),
            },
            "inconsistent",
        ),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 4,
                "status": _status("codex", enabled=False, generation=4),
            },
            "inconsistent",
        ),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 3,
                "status": _status("codex", enabled=False, generation=4),
            },
            "inconsistent",
        ),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 3,
                "status": _status("codex", enabled=False, generation=3),
                "config_revision": "sha256:" + ("b" * 64),
            },
            "Store identity changed",
        ),
        (
            {
                "ok": True,
                "host": "codex",
                "enabled": False,
                "generation": 3,
                "updated_at": "after",
                "source": "dashboard",
                "status": _status("codex", enabled=False, generation=3),
            },
            "provenance",
        ),
    ],
)
def test_dashboard_soft_control_rejects_mismatched_toggle_receipts(
    monkeypatch: pytest.MonkeyPatch,
    toggle: dict[str, Any],
    message: str,
) -> None:
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda path, **_kwargs: _snapshot() if path == "/api/hosts" else {**_identity(), **toggle},
    )
    with pytest.raises(ValueError, match=message):
        install_commands._dashboard_soft_control_result("codex", enabled=False, dry_run=False)


def test_restricted_cli_host_control_uses_broker_and_contains_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[dict[str, Any]] = []
    dependencies = install_commands.InstallDependencies(
        store_factory=_restricted_store,
        emit_json=emitted.append,
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_soft_control_result",
        lambda host, **_kwargs: {
            "ok": True,
            "exit_code": 0,
            "host": host,
            "runtime_enabled": False,
        },
    )
    assert install_commands.cmd_off(_args(), dependencies=dependencies) == 0
    assert emitted[-1]["host"] == "codex"

    monkeypatch.setattr(
        install_commands,
        "_dashboard_soft_control_result",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("broker malformed")),
    )
    assert install_commands.cmd_off(_args(), dependencies=dependencies) == 1
    assert emitted[-1]["ok"] is False
    assert emitted[-1]["error"] == "broker malformed"


def test_host_control_brokers_a_restricted_store_operation_after_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        install_commands,
        "_soft_control_result",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RestrictedWindowsTokenError("restricted process token")
        ),
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_soft_control_result",
        lambda host, **_kwargs: calls.append(host) or {"ok": True, "host": host},
    )

    result = install_commands._restricted_aware_soft_control_result(
        object(),
        "codex",
        enabled=False,
        dry_run=False,
        restricted_store=False,
    )
    direct_broker = install_commands._restricted_aware_soft_control_result(
        None,
        "claude",
        enabled=True,
        dry_run=True,
        restricted_store=True,
    )

    assert result == {"ok": True, "host": "codex"}
    assert direct_broker == {"ok": True, "host": "claude"}
    assert calls == ["codex", "claude"]


def test_restricted_cli_status_correlates_host_and_inference_broker_snapshots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[dict[str, Any]] = []
    dependencies = install_commands.InstallDependencies(
        store_factory=_restricted_store,
        emit_json=emitted.append,
    )
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(True, generation=1), "direct"),
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_host_snapshot_with_identity",
        lambda agent: (
            [_status(agent or "codex", master_enabled=False)],
            _master(False),
            _broker_identity(),
        ),
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_inference_snapshot_with_identity",
        lambda: (_inference(), _broker_identity()),
    )

    assert install_commands.cmd_status(_args(), dependencies=dependencies) == 0
    assert emitted[-1]["master"] == _master(False)
    assert emitted[-1]["master_transport"] == "dashboard"
    assert emitted[-1]["hosts"][0]["master_enabled"] is False
    assert emitted[-1]["inference"] == _inference()


def test_restricted_cli_status_rejects_cross_snapshot_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emitted: list[dict[str, Any]] = []
    dependencies = install_commands.InstallDependencies(
        store_factory=_restricted_store,
        emit_json=emitted.append,
    )
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(), "direct"),
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_host_snapshot_with_identity",
        lambda _agent: ([_status("codex")], _master(), _broker_identity()),
    )
    changed = install_commands._BrokerStoreIdentity(
        config_path=_broker_identity().config_path,
        config_revision="sha256:" + ("b" * 64),
        store_path=_broker_identity().store_path,
        environment_overrides=_broker_identity().environment_overrides,
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_inference_snapshot_with_identity",
        lambda: (_inference(), changed),
    )

    assert install_commands.cmd_status(_args(), dependencies=dependencies) == 1
    assert "changed configuration" in emitted[-1]["error"]


@pytest.mark.parametrize("json_output", [True, False])
def test_restricted_cli_status_reports_broker_failure_without_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    json_output: bool,
) -> None:
    emitted: list[dict[str, Any]] = []
    dependencies = install_commands.InstallDependencies(
        store_factory=_restricted_store,
        emit_json=emitted.append,
    )
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(), "direct"),
    )
    monkeypatch.setattr(
        install_commands,
        "_dashboard_host_snapshot_with_identity",
        lambda _agent: (_ for _ in ()).throw(ValueError("service absent")),
    )

    assert install_commands.cmd_status(_args(json=json_output), dependencies=dependencies) == 1
    if json_output:
        assert emitted[-1]["ok"] is False
        assert emitted[-1]["hosts"] == []
        assert "service absent" in emitted[-1]["error"]
    else:
        assert "service absent" in capsys.readouterr().out


def test_master_broker_requires_exact_shape_state_and_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import runtime_control

    current = _master(True, generation=7)
    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (current, "direct"),
    )
    monkeypatch.setattr(
        runtime_control,
        "set_master_enabled",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runtime_control.RuntimeControlSecurityError("restricted")
        ),
    )
    valid = {
        "ok": True,
        "changed": True,
        "master": _master(False, generation=8),
    }
    monkeypatch.setattr(dashboard_runtime, "dashboard_api_request", lambda *_args, **_kw: valid)

    result = install_commands._global_control_result(
        _args(global_control=True),
        enabled=False,
    )

    assert result["master"]["generation"] == 8
    assert result["transport"] == "dashboard"


@pytest.mark.parametrize(
    "response",
    [
        {"changed": True, "master": _master(False, generation=8)},
        {"ok": True, "changed": 1, "master": _master(False, generation=8)},
        {"ok": True, "changed": False, "master": _master(False, generation=8)},
        {"ok": True, "changed": True, "master": _master(True, generation=8)},
        {"ok": True, "changed": True, "master": _master(False, generation=7)},
        {"ok": True, "changed": True, "master": _master(False, generation=9)},
    ],
)
def test_master_broker_rejects_invalid_transition_receipts(
    monkeypatch: pytest.MonkeyPatch,
    response: dict[str, Any],
) -> None:
    from agency_runtime.core import runtime_control

    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(True, generation=7), "direct"),
    )
    monkeypatch.setattr(
        runtime_control,
        "set_master_enabled",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            runtime_control.RuntimeControlSecurityError("restricted")
        ),
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda *_args, **_kwargs: response,
    )

    with pytest.raises(ValueError, match="master-control response"):
        install_commands._global_control_result(_args(global_control=True), enabled=False)


def test_master_read_broker_rejects_extra_top_level_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import runtime_control

    monkeypatch.setattr(
        runtime_control,
        "read_effective_runtime_control",
        lambda: (_ for _ in ()).throw(runtime_control.RuntimeControlSecurityError("restricted")),
    )
    monkeypatch.setattr(
        runtime_control,
        "_restricted_windows_control_target",
        lambda _path: True,
    )
    monkeypatch.setattr(
        dashboard_runtime,
        "dashboard_api_request",
        lambda *_args, **_kwargs: {"master": _master(), "extra": True},
    )

    with pytest.raises(RuntimeError, match="could not broker"):
        install_commands._read_master_control_with_broker()


def test_master_read_reports_non_brokerable_control_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import runtime_control

    monkeypatch.setattr(
        runtime_control,
        "read_authoritative_runtime_control",
        lambda: (_ for _ in ()).throw(
            runtime_control.RuntimeControlValidationError("corrupt custom control")
        ),
    )

    with pytest.raises(RuntimeError, match="could not be read securely"):
        install_commands._read_master_control_with_broker()


def test_direct_master_write_rejects_inconsistent_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import runtime_control

    monkeypatch.setattr(
        install_commands,
        "_read_master_control_with_broker",
        lambda: (_master(True, generation=7), "direct"),
    )
    monkeypatch.setattr(
        runtime_control,
        "set_master_enabled",
        lambda *_args, **_kwargs: _master(True, generation=7),
    )

    with pytest.raises(ValueError, match="internally inconsistent"):
        install_commands._global_control_result(_args(global_control=True), enabled=False)
