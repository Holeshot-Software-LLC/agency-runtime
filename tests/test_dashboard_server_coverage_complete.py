"""Complete dashboard server error, lifecycle, and platform branch coverage."""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import contextmanager
from http.client import HTTPConnection
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core.config import reset_config_cache
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import dashboard as dashboard


def _verified_codex_record() -> dict[str, object]:
    return {
        "host": "codex",
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "managed_plugin_version": "test",
        "launcher_artifacts_current": True,
    }


@contextmanager
def _running_dashboard(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(tmp_path / "agency.yaml"))
    monkeypatch.setenv("AGENCY_DB_PATH", str(tmp_path / "agency.db"))
    reset_config_cache()
    store = Store(tmp_path / "agency.db")
    token = "coverage-token"
    server = dashboard.DashboardHTTPServer(
        store,
        auth_token=token,
        port=0,
        host_inspector=lambda: [_verified_codex_record()],
        runtime_control_home=tmp_path,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield SimpleNamespace(
            base=f"http://127.0.0.1:{server.server_address[1]}",
            port=int(server.server_address[1]),
            token=token,
            store=store,
            server=server,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
        reset_config_cache()


def _request(
    server: SimpleNamespace,
    path: str,
    *,
    method: str = "GET",
    body: object | None = None,
    content_type: str = "application/json",
    origin: str | None = None,
) -> tuple[int, dict[str, Any]]:
    headers = {"Authorization": f"Bearer {server.token}"}
    if origin is not None:
        headers["Origin"] = origin
    data = None
    if body is not None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        headers["Content-Type"] = content_type
    request = urllib.request.Request(
        f"{server.base}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        with exc:
            return exc.code, json.loads(exc.read())


def _direct_dashboard_handler(
    store: object,
    path: str,
) -> tuple[dashboard.DashboardHTTPHandler, list[dict[str, Any]]]:
    handler = object.__new__(dashboard.DashboardHTTPHandler)
    handler.path = path
    handler.server = SimpleNamespace(
        store=store,
        config_path="C:\\agency.yaml",
        host_inspector=lambda: [],
    )
    responses: list[dict[str, Any]] = []
    handler._json_ok = responses.append
    return handler, responses


def _dashboard_state(*, disabled: tuple[str, ...] = ()) -> SimpleNamespace:
    return SimpleNamespace(
        path="C:\\agency.yaml",
        persisted={},
        effective={"agents": {"disabled": list(disabled)}},
        revision="config-revision",
        secret_presence={},
        environment_overrides=[],
    )


def test_dashboard_exposes_authenticated_account_model_catalog(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, bool]] = []

    class Catalog:
        def as_dict(self) -> dict[str, Any]:
            return {
                "transport": "codex",
                "models": [{"slug": "gpt-cheap", "display_name": "Cheap"}],
                "source": "codex-cli",
                "error": "",
            }

    monkeypatch.setattr(
        dashboard,
        "discover_cli_models",
        lambda transport, *, refresh=False: calls.append((transport, refresh)) or Catalog(),
    )
    with _running_dashboard(tmp_path, monkeypatch) as server:
        status, payload = _request(
            server,
            "/api/providers/models?transport=codex&refresh=true",
        )
        assert status == 200
        assert payload["models"][0]["slug"] == "gpt-cheap"
        assert calls == [("codex", True)]


def test_dashboard_miscellaneous_get_post_and_options_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        request = urllib.request.Request(f"{server.base}/api/health", method="OPTIONS")
        with pytest.raises(urllib.error.HTTPError) as denied:
            urllib.request.urlopen(request, timeout=5)
        with denied.value as error:
            assert error.code == 405

        assert _request(server, "/outside")[0] == 404
        assert _request(server, "/api/health") == (200, {"status": "ok"})
        assert _request(server, "/api/roster")[0] == 200
        assert _request(server, "/api/snapshots")[0] == 200
        status, payload = _request(server, "/api/activity?limit=invalid")
        assert status == 400
        assert payload["error"] == "collection result limit must be an integer"
        assert _request(server, "/api/unknown")[0] == 404
        assert _request(server, "/outside", method="POST", body={})[0] == 404
        assert _request(server, "/api/unknown", method="POST", body={})[0] == 404

        for body in (
            {"operations": {}, "confirmations": []},
            {"operations": [], "confirmations": [1]},
        ):
            status, payload = _request(
                server,
                "/api/config",
                method="POST",
                body=body,
            )
            assert status == 403
            assert "read-only" in payload["error"]


def test_dashboard_confirmation_helper_and_default_host_inspector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    required = dashboard._required_config_confirmations(
        [
            object(),
            {"op": "set", "path": "profile", "value": 1},
            {"op": "secret"},
            {"op": "set", "path": "profile", "value": " local-only "},
            {"op": "set", "path": "observability.capture_content", "value": True},
        ]
    )
    assert required == {
        "SAVE CONFIG",
        "SAVE SENSITIVE CONFIG",
        "APPLY LOCAL-ONLY PROFILE",
        "ENABLE CONTENT CAPTURE",
    }
    monkeypatch.setattr(
        "agency_runtime.core.installer.inspect_host_installation",
        lambda host: {"host": host, "registered": True},
    )
    assert dashboard._inspect_one_host("codex")["registered"] is True


def test_dashboard_route_lab_pure_projection_edge_matrix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    limit, after, filters = dashboard._roster_operations_query(
        "/api/roster/operations?after=alpha-reviewer&query=security"
    )
    assert limit == dashboard.MAX_OPERATIONAL_ROSTER_RESULTS
    assert after == "alpha-reviewer"
    assert filters == {"query": "security"}

    records, duplicates = dashboard._route_lab_native_records(
        lambda: [
            object(),
            {"host": 7},
            {"host": "browser"},
            {"host": "codex", "registered": True},
            {"host": "codex", "registered": False},
        ]
    )
    assert records["codex"]["registered"] is True
    assert duplicates == frozenset({"codex"})

    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": True},
            None,
        )
        == "authoritative capability receipt is invalid"
    )
    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": False},
            {"status": "unavailable"},
        )
        == "host is not effectively enabled"
    )
    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": None},
            {"status": "unavailable"},
        )
        == "host enablement is unproven"
    )
    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": True},
            {"status": "unavailable", "evidence": ["executable missing"]},
        )
        == "executable missing"
    )
    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": True},
            {"status": "degraded", "evidence": []},
        )
        == "capability status is degraded"
    )
    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": True},
            {"status": "degraded", "evidence": [object(), ""]},
        )
        == "capability status is degraded"
    )
    assert (
        dashboard._route_lab_host_failure(
            {"effective_enabled": True},
            {"status": "degraded"},
        )
        == "capability status is degraded"
    )

    monkeypatch.setattr(
        "agency_runtime.core.host_control.inspect_host_status",
        lambda *_args, **_kwargs: {
            "effective_enabled": False,
            "execution_capabilities": None,
        },
    )
    with pytest.raises(ValueError, match="none is available"):
        dashboard._route_lab_host_capability(
            object(),  # type: ignore[arg-type]
            lambda: [],
            requested_host=None,
            global_enabled=True,
        )

    projection = dashboard._route_lab_eligibility_projection(
        {
            "routing": {
                "eligibility_rejections": [
                    "opaque",
                    {"slug": "alpha", "reason": "unsupported host"},
                    {"slug": "", "reason": "missing slug"},
                ]
            }
        },
        {
            "execution_host": "codex",
            "status": "native-installation-verified",
        },
        catalog_size=3,
    )
    assert projection["eligible_count"] == 0
    assert projection["rejections"] == [{"slug": "alpha", "reason": "unsupported host"}]


def test_dashboard_activity_projection_strips_optional_content_fields() -> None:
    source = {
        "runs": [{"id": "run-1"}],
        "routing": [{"id": "route-1", "work_units": ["private"], "status": "ok"}],
        "delegations": [{"id": "delegation-1", "skip_reason": "private", "status": "completed"}],
        "receipts": [],
        "finalizations": [],
        "specialists": [{"id": "specialist-1", "slug": "reviewer", "prompt_body": "private"}],
    }

    rendered = dashboard._dashboard_activity(source)

    assert rendered["runs"] is source["runs"]
    assert rendered["routing"] == [{"id": "route-1", "status": "ok"}]
    assert rendered["delegations"] == [{"id": "delegation-1", "status": "completed"}]
    assert rendered["specialists"] == [{"id": "specialist-1", "slug": "reviewer"}]


def test_dashboard_collection_cursors_are_canonical_and_fail_closed() -> None:
    assert dashboard._bounded_query_limit("/api/live?limit=invalid", default=17) == 17
    assert dashboard._bounded_query_limit("/api/live?limit=-1", default=17) == 1
    assert dashboard._bounded_query_limit("/api/live?limit=1000", default=17) == 200

    kind = "activity.routing.v1"
    cursor = dashboard._encode_collection_cursor(kind, "2026-07-26T00:00:00Z", "route-1")
    assert dashboard._decode_collection_cursor(cursor, kind=kind, fields=2) == (
        "2026-07-26T00:00:00Z",
        "route-1",
    )

    invalid = (
        "",
        "invalid$",
        "ew",
        "__8",
        dashboard._encode_collection_cursor("activity.runs.v1", "time", "id"),
        dashboard._encode_collection_cursor(kind, "time"),
        dashboard._encode_collection_cursor(kind, "", "id"),
        dashboard._encode_collection_cursor(kind, "time", 7),
    )
    for value in invalid:
        with pytest.raises(ValueError, match="collection cursor is invalid"):
            dashboard._decode_collection_cursor(value, kind=kind, fields=2)


def test_dashboard_activity_collection_returns_a_stripped_keyset_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming = dashboard._encode_collection_cursor(
        "activity.routing.v1",
        "2026-07-26T00:00:02Z",
        "route-2",
    )
    calls: list[tuple[object, ...]] = []

    def activity_page(kind: str, **kwargs: Any) -> dict[str, Any]:
        calls.append((kind, kwargs))
        return {
            "rows": [
                {
                    "id": "route-1",
                    "created_at": "2026-07-26T00:00:01Z",
                    "work_units": ["private"],
                    "status": "selected",
                }
            ],
            "next_time": "2026-07-26T00:00:01Z",
            "next_id": "route-1",
            "page_count": 1,
            "filtered_count": 2,
            "total_count": 4,
            "limit": 1,
            "truncated": True,
            "collection_revision": "activity-revision",
        }

    store = SimpleNamespace(dashboard_activity_page=activity_page)
    handler, responses = _direct_dashboard_handler(
        store,
        f"/api/activity?kind=routing&limit=1&after={incoming}",
    )
    state = _dashboard_state()
    binding = {
        "store_path": "C:\\agency.db",
        "desired_store_path": "C:\\agency.db",
        "store_restart_required": False,
    }
    monkeypatch.setattr(dashboard, "read_config_state", lambda _path: state)
    monkeypatch.setattr(dashboard, "_store_service_binding", lambda _store, _state: binding)

    handler._handle_activity()

    assert calls == [
        (
            "routing",
            {
                "limit": 1,
                "after_time": "2026-07-26T00:00:02Z",
                "after_id": "route-2",
            },
        )
    ]
    response = responses.pop()
    assert response["schema_version"] == "agency.dashboard.activity_collection.v1"
    assert response["items"] == [
        {
            "id": "route-1",
            "created_at": "2026-07-26T00:00:01Z",
            "status": "selected",
        }
    ]
    assert response["truncated"] is True
    assert response["filtered_count"] == 2
    assert response["total_count"] == 4
    assert dashboard._decode_collection_cursor(
        response["next_cursor"],
        kind="activity.routing.v1",
        fields=2,
    ) == ("2026-07-26T00:00:01Z", "route-1")


def test_dashboard_control_contract_covers_restart_and_truncated_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _dashboard_state(disabled=("agent-000",))
    binding = {
        "store_path": "C:\\active.db",
        "desired_store_path": "C:\\desired.db",
        "store_restart_required": True,
    }
    monkeypatch.setattr(dashboard, "read_config_state", lambda _path: state)
    monkeypatch.setattr(dashboard, "_store_service_binding", lambda _store, _state: binding)
    monkeypatch.setattr(
        dashboard,
        "_require_store_service_binding",
        lambda _store, _state: binding,
    )

    restart_handler, restart_responses = _direct_dashboard_handler(object(), "/api/control")
    restart_handler._handle_control()
    restart = restart_responses.pop()
    assert restart["restart_required"] is True
    assert "hosts" not in restart
    restart_core = {
        key: value
        for key, value in restart.items()
        if key not in {"sampled_at", "control_revision"}
    }
    assert restart["control_revision"] == dashboard._dashboard_revision(restart_core)

    class ControlStore:
        def get_active_roster_ui_page_snapshot(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "rows": [{"slug": f"agent-{index:03}"} for index in range(201)],
                "total_count": 201,
                "enabled_count": 200,
                "generation": 7,
            }

        def roster_snapshot_page(self, **_kwargs: Any) -> dict[str, Any]:
            return {
                "rows": [{"snapshot_id": "snapshot-1"}],
                "total_count": 1,
                "truncated": False,
                "next_created_at": "",
                "next_snapshot_id": "",
                "collection_revision": "snapshot-revision",
            }

    binding.update(
        desired_store_path="C:\\active.db",
        store_restart_required=False,
    )
    monkeypatch.setattr(
        dashboard,
        "ui_roster_projection",
        lambda agent, disabled: {
            "agent_slug": agent["slug"],
            "enabled": agent["slug"] not in disabled,
        },
    )
    monkeypatch.setattr(
        dashboard,
        "roster_operational_page",
        lambda _store, **_kwargs: {"agents": [], "count": 0, "roster_generation": 7},
    )
    monkeypatch.setattr(
        dashboard,
        "candidate_review_snapshot",
        lambda _store: {
            "candidates": [],
            "filtered_count": 0,
            "total_count": 0,
            "truncated": False,
            "next_candidate_time": "",
            "next_candidate_id": "",
            "collection_revision": "review-revision",
        },
    )
    handler, responses = _direct_dashboard_handler(ControlStore(), "/api/control")
    handler._master_control = lambda: {"enabled": True, "generation": 3}
    handler._host_payload = lambda _master: [{"host": "codex", "registered": True}]

    handler._handle_control()

    response = responses.pop()
    assert response["restart_required"] is False
    assert response["hosts"] == [{"host": "codex", "registered": True}]
    assert response["roster"]["count"] == 200
    assert response["roster"]["total_count"] == 201
    assert response["roster"]["enabled_count"] == 200
    assert response["roster"]["disabled_count"] == 1
    assert response["roster"]["truncated"] is True
    assert response["roster"]["next_cursor"] == "agent-199"
    assert response["governance"]["snapshots"] == [{"snapshot_id": "snapshot-1"}]
    core = {
        key: value
        for key, value in response.items()
        if key not in {"sampled_at", "control_revision"}
    }
    assert response["control_revision"] == dashboard._dashboard_revision(core)


def test_control_roster_capture_recaptures_and_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class InterleavedStore:
        def __init__(self, generations: list[int]) -> None:
            self.generations = iter(generations)
            self.calls = 0

        def get_active_roster_ui_page_snapshot(self, **_kwargs: Any) -> dict[str, Any]:
            self.calls += 1
            return {"generation": next(self.generations)}

    matching = InterleavedStore([3, 4])
    operation_generations = iter([4, 4])
    monkeypatch.setattr(
        dashboard,
        "roster_operational_page",
        lambda _store, **_kwargs: {"roster_generation": next(operation_generations)},
    )
    roster, operations = dashboard._capture_consistent_control_roster(
        matching,
        disabled_agents=frozenset(),
    )
    assert matching.calls == 2
    assert roster["generation"] == operations["roster_generation"] == 4

    changing = InterleavedStore([10, 11, 12])
    operation_generations = iter([11, 12, 13])
    with pytest.raises(RuntimeError, match="changed during bounded capture"):
        dashboard._capture_consistent_control_roster(
            changing,
            disabled_agents=frozenset(),
        )
    assert changing.calls == dashboard._CONTROL_SNAPSHOT_CAPTURE_ATTEMPTS


def test_dashboard_post_runtime_control_failure_is_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "private runtime-control path"
    warnings: list[tuple[object, ...]] = []

    def fail_route(_handler: object, _body: dict[str, Any]) -> None:
        raise dashboard.RuntimeControlError(secret)

    monkeypatch.setattr(dashboard.DashboardHTTPHandler, "_handle_route_lab", fail_route)
    monkeypatch.setattr(dashboard.logger, "warning", lambda *args: warnings.append(args))
    with _running_dashboard(tmp_path, monkeypatch) as server:
        status, payload = _request(
            server,
            "/api/route",
            method="POST",
            body={"task": "review security"},
        )

    assert status == 400
    assert payload == {"error": "runtime control unavailable"}
    assert warnings == [
        (
            "dashboard POST runtime-control error for %s (%s)",
            "route",
            "RuntimeControlError",
        )
    ]
    assert secret not in repr(warnings)


def test_dashboard_rejects_bad_host_same_origin_mismatch_and_invalid_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        connection = HTTPConnection("127.0.0.1", server.port, timeout=5)
        connection.putrequest("GET", "/api/health", skip_host=True)
        connection.putheader("Host", "attacker.invalid")
        connection.putheader("Authorization", f"Bearer {server.token}")
        connection.endheaders()
        response = connection.getresponse()
        assert response.status == 400
        assert json.loads(response.read())["error"] == "invalid Host header"
        connection.close()

        assert (
            _request(
                server,
                "/api/health",
                origin=f"http://127.0.0.1:{server.port}/",
            )[0]
            == 200
        )

        status, payload = _request(
            server,
            "/api/route",
            method="POST",
            body=b"{invalid",
        )
        assert status == 400
        assert "JSON" in payload["error"]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({}, "task is required"),
        (
            {"task": "x", "limit": object()},
            "limit must be an integer from 1 through 50",
        ),
    ],
)
def test_dashboard_route_lab_validation_is_strict(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, Any],
    message: str,
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        if body.get("limit") is not None:
            body["limit"] = {"invalid": True}
        status, payload = _request(server, "/api/route", method="POST", body=body)
        assert status == 400
        assert payload["error"] == message


def test_dashboard_route_lab_rejects_oversized_task(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        maximum = dashboard.load_config().selector.max_user_msg_len
        status, payload = _request(
            server,
            "/api/route",
            method="POST",
            body={"task": "x" * (maximum + 1)},
        )
        assert status == 400
        assert "maximum" in payload["error"]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"confirm": "TRIM RUNTIME DATA", "older_than_days": True},
        {"confirm": "TRIM RUNTIME DATA", "older_than_days": 30, "dry_run": "yes"},
        {"confirm": "TRIM RUNTIME DATA", "older_than_days": 30, "vacuum": "yes"},
    ],
)
def test_dashboard_trim_is_denied_before_payload_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    body: dict[str, Any],
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        status, payload = _request(server, "/api/maintenance/trim", method="POST", body=body)
        assert status == 403
        assert "read-only" in payload["error"]


def test_dashboard_roster_actions_are_denied_before_dispatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        dashboard,
        "approve_snapshot",
        lambda _store, snapshot, **_kwargs: calls.append(("approve", snapshot)),
    )
    monkeypatch.setattr(
        dashboard,
        "activate_snapshot",
        lambda _store, snapshot, **_kwargs: calls.append(("activate", snapshot)),
    )
    with _running_dashboard(tmp_path, monkeypatch) as server:
        bodies = [
            {},
            {"action": "approve", "snapshot_id": "one", "confirm": "wrong"},
            {"action": "approve", "snapshot_id": "one", "confirm": "APPROVE one"},
            {"action": "activate", "snapshot_id": "one", "confirm": "ACTIVATE one"},
        ]
        for body in bodies:
            status, payload = _request(
                server,
                "/api/roster/action",
                method="POST",
                body=body,
            )
            assert status == 403
            assert "read-only" in payload["error"]
    assert calls == []


def test_dashboard_host_toggle_is_denied_before_payload_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        bodies = [
            {},
            {"host": "codex", "enabled": "yes"},
            {
                "host": "codex",
                "enabled": False,
                "expected_generation": 0,
                "confirm": "wrong",
            },
            {
                "host": "codex",
                "enabled": False,
                "expected_generation": 0,
                "confirm": "DISABLE codex",
            },
        ]
        for body in bodies:
            status, payload = _request(server, "/api/hosts/toggle", method="POST", body=body)
            assert status == 403
            assert "read-only" in payload["error"]


def test_dashboard_json_serialization_failure_is_redacted() -> None:
    sent: list[tuple[str, Any]] = []
    handler = object.__new__(dashboard.DashboardHTTPHandler)
    handler.send_response = lambda status: sent.append(("status", status))
    handler.send_header = lambda name, value: sent.append((name, value))
    handler.end_headers = lambda: None
    handler.wfile = SimpleNamespace(write=lambda value: sent.append(("body", value)))
    handler._send_json(200, {"invalid": object()})
    assert ("status", 500) in sent
    assert ("body", b'{"error":"internal serialization error"}') in sent


def test_dashboard_get_and_post_unexpected_failures_are_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _running_dashboard(tmp_path, monkeypatch) as server:
        monkeypatch.setattr(
            Store,
            "roster_snapshot_page",
            lambda _self, **_kwargs: (_ for _ in ()).throw(TypeError("private get detail")),
        )
        status, payload = _request(server, "/api/snapshots")
        assert status == 500
        assert payload == {"error": "internal server error"}

        monkeypatch.setattr(
            dashboard,
            "explain_route",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(TypeError("private post detail")),
        )
        status, payload = _request(
            server,
            "/api/route",
            method="POST",
            body={"task": "review security"},
        )
        assert status == 500
        assert payload == {"error": "internal server error"}


def test_host_inspection_coordinator_error_stale_and_invalidation() -> None:
    calls = {"value": 0}

    def inspect(host: str) -> dict[str, Any]:
        calls["value"] += 1
        if calls["value"] == 1:
            raise RuntimeError("private detail")
        return {"host": host, "registered": True, "enabled": True}

    executor = ThreadPoolExecutor(max_workers=1)
    coordinator = dashboard._HostInspectionCoordinator(
        inspect_one=inspect,
        hosts=("codex",),
        cache_seconds=0,
        deadline_seconds=1,
        executor=executor,
    )
    try:
        failed = coordinator.inspect()[0]
        assert failed["inspection_status"] in {"error", "stale"}
        coordinator.invalidate("codex")
        complete = coordinator.inspect()[0]
        assert complete["inspection_status"] in {"complete", "stale"}
        # A current cached result avoids submission and the wait path.
        coordinator._cache["codex"] = (
            dashboard.monotonic() + 10,
            {"host": "codex", "inspection_status": "complete"},
        )
        assert coordinator.inspect()[0]["inspection_status"] == "complete"

        stale_future: Future[dict[str, Any]] = Future()
        replacement: Future[dict[str, Any]] = Future()
        coordinator._in_flight["codex"] = replacement
        stale_future.set_result({"registered": False})
        coordinator._finished("codex", stale_future)
        assert coordinator._in_flight["codex"] is replacement
        coordinator.invalidate()
        assert not coordinator._in_flight
    finally:
        executor.shutdown(wait=True, cancel_futures=True)


def test_host_inspection_deadline_returns_explicit_unknown() -> None:
    release = threading.Event()

    def slow(_host: str) -> dict[str, Any]:
        release.wait(timeout=2)
        return {"registered": True}

    executor = ThreadPoolExecutor(max_workers=1)
    coordinator = dashboard._HostInspectionCoordinator(
        inspect_one=slow,
        hosts=("codex",),
        cache_seconds=1,
        deadline_seconds=0,
        executor=executor,
    )
    try:
        assert coordinator.inspect()[0]["inspection_status"] == "timed_out"
        coordinator.invalidate()
    finally:
        release.set()
        executor.shutdown(wait=True, cancel_futures=True)


def test_host_inspection_reuses_an_existing_inflight_future() -> None:
    executor = ThreadPoolExecutor(max_workers=1)
    coordinator = dashboard._HostInspectionCoordinator(
        inspect_one=lambda host: {"host": host},
        hosts=("codex",),
        deadline_seconds=0,
        executor=executor,
    )
    future: Future[dict[str, Any]] = Future()
    coordinator._in_flight["codex"] = future
    try:
        assert coordinator.inspect()[0]["inspection_status"] == "timed_out"
    finally:
        future.cancel()
        coordinator.invalidate()
        executor.shutdown(wait=True, cancel_futures=True)


def test_dashboard_server_rejects_non_loopback_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="loopback-only"):
        dashboard.DashboardHTTPServer(
            Store(tmp_path / "agency.db"),
            auth_token="token",
            host="0.0.0.0",
        )


@pytest.mark.runtime_configuration_identity
def test_run_dashboard_service_lifecycle_and_browser_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    events: list[tuple[str, Any]] = []
    trim_failure = {"enabled": False}

    class _Store:
        def __init__(self, path: object | None = None, **kwargs: Any) -> None:
            events.append(("store", (path, kwargs)))

        def trim_runtime_tables(self, **kwargs: Any) -> None:
            events.append(("trim", kwargs))
            if trim_failure["enabled"]:
                raise RuntimeError("provider-secret-must-not-be-logged")

    class _Server:
        server_address = ("127.0.0.1", 8123)

        def __init__(self, *_args: Any, **kwargs: Any) -> None:
            events.append(("server", kwargs))

        def serve_forever(self, **kwargs: Any) -> None:
            events.append(("serve", kwargs))
            raise KeyboardInterrupt

        def server_close(self) -> None:
            events.append(("close", None))

        def shutdown(self) -> None:
            events.append(("shutdown", None))

    config = SimpleNamespace(
        dashboard=SimpleNamespace(port=8123),
        observability=SimpleNamespace(retention_days=30),
        store=SimpleNamespace(resolved_path=lambda: tmp_path / "default.db"),
    )
    monkeypatch.setattr(dashboard, "load_config", lambda *_args, **_kwargs: config)
    monkeypatch.setattr(dashboard, "Store", _Store)
    monkeypatch.setattr(dashboard, "DashboardHTTPServer", _Server)
    monkeypatch.setattr(dashboard.secrets, "token_urlsafe", lambda _size: "token")
    monkeypatch.setattr(
        dashboard,
        "write_dashboard_runtime",
        lambda **kwargs: events.append(("write", kwargs)),
    )
    monkeypatch.setattr(
        dashboard,
        "remove_dashboard_runtime",
        lambda **kwargs: events.append(("remove", kwargs)),
    )
    monkeypatch.setattr(dashboard, "current_thread", lambda: object())
    monkeypatch.setattr(dashboard, "main_thread", lambda: object())

    class _RetentionThread:
        def __init__(self, *, target: Any, daemon: bool, name: str = "") -> None:
            assert daemon is True
            assert name == "agency-dashboard-retention"
            self.target = target

        def start(self) -> None:
            self.target()

        def join(self, *, timeout: float) -> None:
            assert timeout == 0.5

    monkeypatch.setattr(dashboard, "Thread", _RetentionThread)

    dashboard.run_dashboard(
        db_path=tmp_path / "service.db",
        port=0,
        service_mode=True,
        config_path=tmp_path / "agency.yaml",
        home_dir=tmp_path / "home",
    )
    assert any(name == "write" for name, _value in events)
    assert any(name == "remove" for name, _value in events)
    assert [name for name, _value in events].index("write") < [
        name for name, _value in events
    ].index("trim")

    events.clear()
    opened: list[str] = []
    warnings: list[tuple[str, str]] = []
    trim_failure["enabled"] = True
    monkeypatch.setattr(dashboard.webbrowser, "open", lambda url, new: opened.append(url))
    monkeypatch.setattr(
        dashboard.logger,
        "warning",
        lambda message, error_type: warnings.append((message, error_type)),
    )
    dashboard.run_dashboard(port=0, open_browser=True)
    assert opened == ["http://127.0.0.1:8123/#token=token"]
    assert "access token is temporary" in capsys.readouterr().out
    assert warnings == [("dashboard retention maintenance failed: %s", "RuntimeError")]
    assert "provider-secret" not in repr(warnings)


def test_run_dashboard_service_rejects_nondurable_environment_before_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = SimpleNamespace(
        dashboard=SimpleNamespace(port=8123),
        observability=SimpleNamespace(retention_days=30),
        providers=(),
        adapters=SimpleNamespace(),
    )
    monkeypatch.setenv("AGENCY_POLICY_PATH", str(tmp_path / "process-policy.yaml"))
    monkeypatch.setattr(dashboard, "load_config", lambda *_args, **_kwargs: config)
    monkeypatch.setattr(
        dashboard,
        "Store",
        lambda *_args, **_kwargs: pytest.fail(
            "service-mode override rejection opened the configured Store"
        ),
    )

    with pytest.raises(RuntimeError, match="AGENCY_POLICY_PATH"):
        dashboard.run_dashboard(
            service_mode=True,
            open_browser=False,
            config_path=tmp_path / "agency.yaml",
        )


def test_run_dashboard_main_thread_signal_lifecycle_and_no_browser(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[str, Any]] = []

    class _Store:
        def __init__(self, _path: object | None = None, **_kwargs: Any) -> None:
            pass

        def trim_runtime_tables(self, **_kwargs: Any) -> None:
            pass

    class _Server:
        server_address = ("127.0.0.1", 8124)

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def serve_forever(self, **_kwargs: Any) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            events.append(("closed", None))

        def shutdown(self) -> None:
            events.append(("shutdown", None))

    class _ImmediateThread:
        def __init__(self, *, target: Any, daemon: bool, name: str = "") -> None:
            assert daemon is True
            self.target = target
            self.name = name

        def start(self) -> None:
            self.target()

        def join(self, *, timeout: float) -> None:
            assert timeout == 0.5

    config = SimpleNamespace(
        dashboard=SimpleNamespace(port=8124),
        observability=SimpleNamespace(retention_days=30),
        store=SimpleNamespace(resolved_path=lambda: tmp_path / "default.db"),
    )
    sentinel = object()
    monkeypatch.setattr(dashboard, "load_config", lambda *_args, **_kwargs: config)
    monkeypatch.setattr(dashboard, "Store", _Store)
    monkeypatch.setattr(dashboard, "DashboardHTTPServer", _Server)
    monkeypatch.setattr(dashboard, "current_thread", lambda: sentinel)
    monkeypatch.setattr(dashboard, "main_thread", lambda: sentinel)
    monkeypatch.setattr(dashboard, "Thread", _ImmediateThread)
    monkeypatch.setattr(dashboard.signal, "getsignal", lambda signum: f"previous-{signum}")

    installed = {"count": 0}

    def set_signal(signum: int, handler: Any) -> None:
        if callable(handler):
            installed["count"] += 1
            if installed["count"] == 1:
                handler(signum, None)
            else:
                raise ValueError("unsupported signal")
        elif str(handler).endswith(str(dashboard.signal.SIGINT)):
            return
        else:
            raise OSError("restore failed")

    monkeypatch.setattr(dashboard.signal, "signal", set_signal)
    monkeypatch.setattr(
        dashboard.webbrowser,
        "open",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("browser opened")),
    )
    dashboard.run_dashboard(
        db_path=tmp_path / "main.db",
        port=8124,
        open_browser=False,
    )
    assert ("shutdown", None) in events
    assert ("closed", None) in events
