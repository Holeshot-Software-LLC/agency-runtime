"""Focused regressions for final production-readiness audit findings."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from importlib.resources import files
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

import pytest

from agency_runtime.adapters import base as adapter_base
from agency_runtime.core import doctor
from agency_runtime.core.config import (
    AdapterEntryConfig,
    AdaptersConfig,
    AgencyConfig,
    reset_config_cache,
)
from agency_runtime.core.store import roster as roster_store
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import dashboard, mcp_tools
from agency_runtime.server import http as http_server

_DASHBOARD_MODULES = (
    "dashboard-core.js",
    "dashboard-config.js",
    "dashboard-render.js",
    "dashboard-live.js",
    "dashboard-actions.js",
)


class _HeaderStore:
    def get_host_control(self, _host: str) -> dict[str, bool]:
        return {"enabled": True}

    def get_run(self, trace_id: str) -> dict[str, str] | None:
        if trace_id != "trace-current":
            return None
        return {
            "trace_id": trace_id,
            "session_id": "current",
            "status": "active",
        }

    def get_specialists_for_trace(self, _session_id: str, _trace_id: str) -> list[str]:
        return []

    def get_completion_evidence_snapshot(
        self,
        session_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        if (session_id, trace_id) != ("current", "trace-current"):
            raise ValueError("trace_id does not identify a recorded Agency turn")
        run = {
            "trace_id": trace_id,
            "session_id": session_id,
            "status": "active",
            "ended_at": None,
            "terminal_finalization_id": None,
            "evidence_revision": 1,
            "request_kind": "nontrivial",
        }
        return {
            "session_id": session_id,
            "trace_id": trace_id,
            "status": "active",
            "request_kind": "nontrivial",
            "evidence_revision": 1,
            "run": run,
            "model_receipt": None,
            "skills": [],
            "specialists": [],
            "delegations": [],
        }

    def is_nontrivial_turn(self, session_id: str, trace_id: str) -> bool | None:
        if (session_id, trace_id) == ("current", "trace-current"):
            return True
        return None


class _TestAdapter(adapter_base.BaseAdapter):
    host_name = "test"

    def is_available(self) -> bool:
        return True

    def get_delegate_backend(self) -> str | None:
        return None

    def _suggested_delegations(
        self,
        _session_id: str,
        _trace_id: str,
    ) -> list[dict[str, Any]]:
        return []


def _valid_none_header() -> str:
    return "\n".join(
        (
            "Agency/Agencies loaded: none",
            "Agency/Agencies delegated: none - no delegation executed",
            "Skills loaded: none",
            "Actual Model selected: requested -> unavailable",
            "Recruited via: none",
            "Why: routing was required",
            "How it shaped outcome: no specialist evidence was recorded",
            "",
            "Response body.",
        )
    )


def _isolate_doctor_inventory_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "_config_checks", lambda _cfg: [])
    monkeypatch.setattr(doctor, "_database_checks", lambda _cfg: [])
    monkeypatch.setattr(doctor, "_provider_validation_map", lambda _cfg: {})
    monkeypatch.setattr(doctor, "_judge_checks", lambda *_args: [])
    monkeypatch.setattr(doctor, "_provider_chain_checks", lambda *_args: [])
    monkeypatch.setattr(doctor, "_http_check", lambda *_args, **_kwargs: (False, "offline"))
    monkeypatch.setattr(
        doctor,
        "inspect_host_installations",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("private path detail")),
    )


def test_nontrivial_turn_evidence_is_store_backed_and_still_enforced() -> None:
    adapter = _TestAdapter(store=_HeaderStore())  # type: ignore[arg-type]
    assert adapter._was_nontrivial_turn("current", "trace-current") is True
    with pytest.raises(RuntimeError, match="could not be verified"):
        adapter._was_nontrivial_turn("unknown", "trace-unknown")
    decision = adapter.enforce_pre_verify(
        _valid_none_header(),
        session_id="current",
        trace_id="trace-current",
    )
    assert decision is not None
    assert decision["action"] == "continue"
    assert "has Agency context" in decision["message"]


@pytest.mark.parametrize(
    ("config", "expected_status"),
    [
        (AgencyConfig(), "DEGRADED"),
        (
            AgencyConfig(adapters=AdaptersConfig(codex=AdapterEntryConfig(enabled="true"))),
            "FAILED",
        ),
    ],
)
def test_doctor_converts_native_inventory_failure_to_structured_report(
    monkeypatch: pytest.MonkeyPatch,
    config: AgencyConfig,
    expected_status: str,
) -> None:
    _isolate_doctor_inventory_failure(monkeypatch)

    report = doctor.run_doctor(config)
    payload = report.to_dict()

    assert payload["status"] == expected_status
    inventory = next(
        check for check in payload["checks"] if check["name"] == "adapter_host_inventory"
    )
    assert inventory["status"] == ("fail" if expected_status == "FAILED" else "warn")
    assert inventory["detail"] == "inspection failed (OSError)"
    assert "private path detail" not in str(payload)


def test_doctor_inventory_failure_keeps_explicitly_disabled_hosts_passing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _isolate_doctor_inventory_failure(monkeypatch)
    disabled = AdapterEntryConfig(enabled="false")
    config = AgencyConfig(
        adapters=AdaptersConfig(
            hermes=disabled,
            openclaw=disabled,
            codex=disabled,
            claude=disabled,
        )
    )

    payload = doctor.run_doctor(config).to_dict()

    assert payload["status"] == "DEGRADED"
    host_checks = {
        check["name"]: check for check in payload["checks"] if check["name"].startswith("adapter_")
    }
    for host in ("hermes", "openclaw", "codex", "claude"):
        assert host_checks[f"adapter_{host}"]["status"] == "pass"


class _RejectingExecutor:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, *_args: Any, **_kwargs: Any) -> Future[dict[str, Any]]:
        self.submissions += 1
        raise AssertionError("running invalidated inspection must be reused")


class _ImmediateExecutor:
    def __init__(self) -> None:
        self.submissions = 0

    def submit(self, fn: Any, host: str) -> Future[dict[str, Any]]:
        self.submissions += 1
        future: Future[dict[str, Any]] = Future()
        future.set_result(fn(host))
        return future


class _BlockingResultFuture(Future[dict[str, Any]]):
    def __init__(self) -> None:
        super().__init__()
        self.entered = Event()
        self.release = Event()
        assert self.set_running_or_notify_cancel() is True

    def result(self, timeout: float | None = None) -> dict[str, Any]:
        self.entered.set()
        if not self.release.wait(timeout=timeout or 1):
            raise TimeoutError("test result was not released")
        return {"registered": False}


def test_dashboard_invalidation_retains_running_future_and_discards_stale_result() -> None:
    rejecting = _RejectingExecutor()
    coordinator = dashboard._HostInspectionCoordinator(
        inspect_one=lambda host: {"host": host, "registered": True},
        hosts=("codex",),
        deadline_seconds=0,
        executor=rejecting,  # type: ignore[arg-type]
    )
    running: Future[dict[str, Any]] = Future()
    assert running.set_running_or_notify_cancel() is True
    coordinator._in_flight["codex"] = running
    coordinator._cache["codex"] = (
        dashboard.monotonic() + 10,
        {"host": "codex", "registered": False},
    )

    coordinator.invalidate("codex")

    assert coordinator._in_flight["codex"] is running
    assert "codex" in coordinator._invalidated
    assert coordinator.inspect()[0]["inspection_status"] == "timed_out"
    assert rejecting.submissions == 0

    running.set_result({"host": "codex", "registered": False})
    coordinator._finished("codex", running)
    assert "codex" not in coordinator._in_flight
    assert "codex" not in coordinator._cache

    immediate = _ImmediateExecutor()
    coordinator.executor = immediate  # type: ignore[assignment]
    refreshed = coordinator.inspect()[0]
    assert refreshed["inspection_status"] == "complete"
    assert refreshed["registered"] is True
    assert immediate.submissions == 1

    pending: Future[dict[str, Any]] = Future()
    coordinator._in_flight["codex"] = pending
    coordinator.invalidate("codex")
    assert pending.cancelled() is True
    assert "codex" not in coordinator._in_flight


def test_dashboard_invalidation_wins_race_after_result_collection_starts() -> None:
    coordinator = dashboard._HostInspectionCoordinator(
        hosts=("codex",),
        deadline_seconds=0,
    )
    future = _BlockingResultFuture()
    coordinator._in_flight["codex"] = future

    with ThreadPoolExecutor(max_workers=1) as executor:
        finished = executor.submit(coordinator._finished, "codex", future)
        assert future.entered.wait(timeout=1)
        coordinator.invalidate("codex")
        assert coordinator._in_flight["codex"] is future
        future.release.set()
        finished.result(timeout=1)

    assert "codex" not in coordinator._in_flight
    assert "codex" not in coordinator._invalidated
    assert "codex" not in coordinator._cache


def test_dashboard_newer_inspection_wins_race_after_result_collection_starts() -> None:
    coordinator = dashboard._HostInspectionCoordinator(
        hosts=("codex",),
        deadline_seconds=0,
    )
    stale = _BlockingResultFuture()
    replacement: Future[dict[str, Any]] = Future()
    coordinator._in_flight["codex"] = stale

    with ThreadPoolExecutor(max_workers=1) as executor:
        finished = executor.submit(coordinator._finished, "codex", stale)
        assert stale.entered.wait(timeout=1)
        coordinator._in_flight["codex"] = replacement
        stale.release.set()
        finished.result(timeout=1)

    assert coordinator._in_flight["codex"] is replacement
    assert "codex" not in coordinator._cache


def test_dashboard_invalidate_all_skips_hosts_without_inflight_work() -> None:
    coordinator = dashboard._HostInspectionCoordinator(
        hosts=("codex", "claude"),
        deadline_seconds=0,
    )
    cached = (dashboard.monotonic() + 10, {"inspection_status": "complete"})
    coordinator._cache.update({"codex": cached, "claude": cached})

    coordinator.invalidate()

    assert coordinator._cache == {}
    assert coordinator._invalidated == set()


def test_dashboard_es_modules_are_exactly_allowlisted_as_javascript() -> None:
    for filename in _DASHBOARD_MODULES:
        assert dashboard._ASSETS[f"/{filename}"] == (
            filename,
            "text/javascript; charset=utf-8",
        )
        resource = files("agency_runtime.dashboard").joinpath(filename)
        assert resource.is_file()
        assert resource.read_bytes()

    assert "/dashboard-extra.js" not in dashboard._ASSETS


def test_dashboard_es_module_routes_serve_only_allowlisted_package_assets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "missing.yaml"))
    reset_config_cache()
    server = dashboard.DashboardHTTPServer(
        Store(tmp_path / "dashboard-assets.db"),
        auth_token="test-token",
        port=0,
        host_inspector=lambda: [],
    )
    thread = Thread(
        target=server.serve_forever,
        kwargs={"poll_interval": 0.01},
        daemon=True,
    )
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        for filename in _DASHBOARD_MODULES:
            with urllib_request.urlopen(f"{base_url}/{filename}", timeout=2) as response:
                assert response.status == 200
                assert response.headers.get_content_type() == "text/javascript"
                assert response.headers.get_content_charset() == "utf-8"
                assert response.read()

        with pytest.raises(urllib_error.HTTPError) as captured:
            urllib_request.urlopen(f"{base_url}/dashboard-extra.js", timeout=2)
        assert captured.value.code == 404
        captured.value.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        reset_config_cache()


def _activate(store: Store, slug: str) -> None:
    store._activate_prevalidated_agent(
        {
            "slug": slug,
            "name": slug.title(),
            "description": f"{slug} specialist",
            "version": "1.0.0",
            "content": f"You are {slug}.",
        }
    )


def test_store_roster_limit_is_applied_in_sql_and_default_remains_compatible(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "roster.db")
    for slug in ("charlie", "alpha", "bravo"):
        _activate(store, slug)

    assert store.count_enabled_roster(disabled_agents=()) == 3
    assert [row["agent_slug"] for row in store.get_active_roster(limit=2)] == [
        "alpha",
        "bravo",
    ]
    assert [row["agent_slug"] for row in store.get_active_roster(after="alpha")] == [
        "bravo",
        "charlie",
    ]
    assert [row["agent_slug"] for row in store.get_active_roster(limit=1, after="alpha")] == [
        "bravo"
    ]
    assert len(store.get_active_roster()) == 3


@pytest.mark.parametrize(
    ("limit", "error"),
    [
        (True, TypeError),
        ("2", TypeError),
        (2.0, TypeError),
        (0, ValueError),
        (roster_store._MAX_ACTIVE_ROSTER_LIMIT + 1, ValueError),
    ],
)
def test_store_roster_limit_rejects_ambiguous_or_out_of_range_values(
    tmp_path: Path,
    limit: Any,
    error: type[Exception],
) -> None:
    store = Store(tmp_path / "invalid-limit.db")
    with pytest.raises(error, match="limit"):
        store.get_active_roster(limit=limit)


@pytest.mark.parametrize(
    ("after", "error"),
    [
        (True, TypeError),
        ("", ValueError),
        ("x" * (roster_store._MAX_ACTIVE_ROSTER_CURSOR_BYTES + 1), ValueError),
    ],
)
def test_store_roster_cursor_rejects_ambiguous_or_unbounded_values(
    tmp_path: Path,
    after: Any,
    error: type[Exception],
) -> None:
    store = Store(tmp_path / "invalid-cursor.db")
    with pytest.raises(error, match="after"):
        store.get_active_roster(after=after)


def test_http_roster_contract_is_bounded_and_reports_truncation() -> None:
    observed: dict[str, Any] = {}

    class RosterStore:
        def get_disabled_agent_slugs(self) -> frozenset[str]:
            return frozenset()

        def count_enabled_roster(self, *, disabled_agents: object) -> int:
            del disabled_agents
            return 3

        def get_enabled_roster(
            self,
            *,
            limit: int,
            after: str | None,
            disabled_agents: object,
        ) -> list[dict[str, Any]]:
            del disabled_agents
            observed["limit"] = limit
            observed["after"] = after
            return [
                {"agent_slug": "alpha"},
                {"agent_slug": "bravo"},
                {"agent_slug": "charlie"},
            ][:limit]

    handler = SimpleNamespace(
        path="/roster?limit=2",
        store=RosterStore(),
        _json_ok=lambda payload: observed.update(payload=payload),
    )

    http_server.AgencyHTTPHandler._handle_roster(handler)  # type: ignore[arg-type]

    assert observed["limit"] == 3
    assert observed["after"] is None
    assert observed["payload"] == {
        "agents": [{"agent_slug": "alpha"}, {"agent_slug": "bravo"}],
        "count": 2,
        "total_count": 3,
        "limit": 2,
        "truncated": True,
        "next_cursor": "bravo",
    }
    assert http_server._bounded_roster_limit("/roster") == 1000
    assert http_server._bounded_roster_limit("/roster?limit=invalid") == 1000
    assert http_server._bounded_roster_limit("/roster?limit=0") == 1
    assert http_server._bounded_roster_limit("/roster?limit=999999") == 1000
    assert http_server._bounded_roster_page("/roster?limit=2&after=alpha") == (2, "alpha")


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("/roster?after=", "after cursor"),
        ("/roster?after=alpha&after=bravo", "at most once"),
        (f"/roster?after={'x' * 1025}", "UTF-8 bytes"),
        ("/roster?after=%3Cscript%3E", "canonical agent slug"),
        ("/roster?after=Alpha", "canonical agent slug"),
        ("/roster?" + "&".join(f"x{i}=1" for i in range(17)), "invalid roster query"),
    ],
)
def test_http_roster_rejects_invalid_cursor_queries(path: str, message: str) -> None:
    observed: dict[str, Any] = {}
    handler = SimpleNamespace(
        path=path,
        store=SimpleNamespace(),
        _json_error=lambda status, detail: observed.update(status=status, detail=detail),
    )

    http_server.AgencyHTTPHandler._handle_roster(handler)  # type: ignore[arg-type]

    assert observed["status"] == 400
    assert message in observed["detail"]


def test_content_length_conversion_failure_returns_bounded_bad_request(monkeypatch) -> None:
    observed: dict[str, Any] = {}

    class Headers:
        def get_all(self, name: str, default: list[str]) -> list[str]:
            return {"Content-Length": ["2"], "Transfer-Encoding": []}.get(name, default)

    def fail_conversion(_value: object) -> int:
        raise ValueError("simulated integer conversion failure")

    handler = SimpleNamespace(
        headers=Headers(),
        close_connection=False,
        _json_error=lambda status, detail: observed.update(status=status, detail=detail),
    )
    with monkeypatch.context() as context:
        context.setattr(http_server, "int", fail_conversion, raising=False)
        result = http_server.AgencyHTTPHandler._read_json_body(handler)  # type: ignore[arg-type]

    assert result is None
    assert handler.close_connection is True
    assert observed == {"status": 400, "detail": "invalid or missing Content-Length"}


def test_http_status_counts_roster_without_materializing_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import runtime_control

    observed: dict[str, Any] = {}
    master = {
        "schema_version": 1,
        "enabled": True,
        "generation": 7,
        "source": "test",
    }
    monkeypatch.setattr(runtime_control, "read_effective_runtime_control", lambda: master)

    class StatusStore:
        db_path = tmp_path / "status.db"

        def count_enabled_roster(self) -> int:
            return 12_345

        def get_active_roster(self) -> list[dict[str, Any]]:
            raise AssertionError("status must not materialize roster rows")

    handler = SimpleNamespace(
        store=StatusStore(),
        _json_ok=lambda payload: observed.update(payload=payload),
    )

    http_server.AgencyHTTPHandler._handle_status(handler)  # type: ignore[arg-type]

    assert observed["payload"] == {
        "status": "ok",
        "runtime_enabled": True,
        "master": master,
        "roster_count": 12_345,
        "db_path": str(tmp_path / "status.db"),
    }


def test_mcp_status_counts_roster_without_materializing_rows(tmp_path: Path) -> None:
    class StatusStore:
        db_path = tmp_path / "mcp-status.db"

        def count_enabled_roster(self) -> int:
            return 54_321

        def get_active_roster(self) -> list[dict[str, Any]]:
            raise AssertionError("MCP status must not materialize roster rows")

        def get_host_control(self, host: str) -> dict[str, Any]:
            return {"host": host, "enabled": True}

    result = mcp_tools._status({}, StatusStore())

    assert result["roster_count"] == 54_321
    assert result["storage"] == {"backend": "sqlite", "binding": "verified"}
    assert "db_path" not in result
    assert str(tmp_path / "mcp-status.db") not in repr(result)
    assert set(result["hosts"]) == {"hermes", "openclaw", "codex", "claude", "zcode"}
