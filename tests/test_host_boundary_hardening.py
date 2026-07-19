"""Regression coverage for host discovery, hooks, diagnostics, and canaries."""

from __future__ import annotations

import io
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core import detect as detect_module
from agency_runtime.core import doctor as doctor_module
from agency_runtime.core.canary import (
    _codex_isolated_plugin_enabled,
    _copy_bounded_auth,
    run_canary,
)
from agency_runtime.core.cli_transport import inspect_cli_transport, invoke_cli_judge
from agency_runtime.core.config import (
    AgencyConfig,
    JudgeConfig,
    ProviderEntry,
    StoreConfig,
)
from agency_runtime.core.detect import AdapterDetection, ProviderDetection
from agency_runtime.core.process_argv import prepare_process_argv
from agency_runtime.core.provider_validation import ProviderValidationResult
from agency_runtime.core.store.sqlite import Store


def test_process_argv_rejects_non_string_items_before_resolution() -> None:
    called = False

    def resolver(_name: str) -> str:
        nonlocal called
        called = True
        return "/bin/agent"

    with pytest.raises(TypeError, match="sequence of strings"):
        prepare_process_argv(["agent", Path("task")], resolver=resolver)  # type: ignore[list-item]

    assert called is False


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 601])
def test_cli_transports_reject_unbounded_timeouts_before_resolution(
    timeout: float,
) -> None:
    called = False

    def resolver(_name: str) -> str:
        nonlocal called
        called = True
        return "/bin/codex"

    status = inspect_cli_transport("codex", timeout=timeout, resolver=resolver)
    judged = invoke_cli_judge(
        ProviderEntry(name="codex", type="cli", transport="codex"),
        "route safely",
        timeout=timeout,
        resolver=resolver,
    )

    assert status.usable is False
    assert "timeout" in status.reason
    assert judged is None
    assert called is False


def test_provider_detection_probes_independent_endpoints_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    barrier = threading.Barrier(4)

    def synchronize() -> None:
        barrier.wait(timeout=2)

    def get_json(_url: str, **_kwargs: Any) -> dict[str, Any]:
        synchronize()
        return {"models": [{"name": "local-model"}]}

    def health(_url: str, _timeout: float = 2.0) -> bool:
        synchronize()
        return True

    def models(base_url: str, _api_key: str | None = None) -> list[str]:
        synchronize()
        return ["remote-model"] if "openai.com" in base_url else ["proxy-model"]

    monkeypatch.setenv("OPENAI_API_KEY", "secret")
    monkeypatch.setattr(detect_module, "_http_get_json", get_json)
    monkeypatch.setattr(detect_module, "_http_check", health)
    monkeypatch.setattr(detect_module, "_fetch_model_list", models)

    result = detect_module.detect_providers()

    assert result.ollama_models == ["local-model"]
    assert result.openai_models == ["remote-model"]
    assert result.litellm_models == ["proxy-model"]


def test_full_detection_runs_provider_host_and_cli_inventory_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    barrier = threading.Barrier(3)

    def providers() -> ProviderDetection:
        barrier.wait(timeout=2)
        return ProviderDetection(ollama_available=True)

    def adapters() -> AdapterDetection:
        barrier.wait(timeout=2)
        return AdapterDetection(codex=True)

    def cli_providers() -> dict[str, Any]:
        barrier.wait(timeout=2)
        return {}

    monkeypatch.setattr(detect_module, "detect_providers", providers)
    monkeypatch.setattr(detect_module, "detect_adapters", adapters)
    monkeypatch.setattr(detect_module, "detect_cli_providers", cli_providers)

    result = detect_module.detect_all()

    assert result.providers.ollama_available is True
    assert result.adapters.codex is True


def test_adapter_detection_uses_canonical_native_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.installer.detect_installed_agents",
        lambda: ["hermes", "openclaw"],
    )

    detected = detect_module.detect_adapters()

    assert detected == AdapterDetection(hermes=True, openclaw=True)


def test_host_adapter_availability_uses_canonical_inventory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        "agency_runtime.core.installer.detect_installed_agents",
        lambda: ["hermes"],
    )
    store = Store(tmp_path / "agency.db")

    assert HermesAdapter(store=store).is_available() is True
    assert OpenClawAdapter(store=store).is_available() is False


def test_doctor_does_not_create_a_missing_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing" / "agency.db"
    config = AgencyConfig(
        store=StoreConfig(db_path=str(db_path)),
        judge=JudgeConfig(
            model="local-model",
            base_url="http://127.0.0.1:1",
            ollama_mode=True,
        ),
    )
    monkeypatch.setattr(doctor_module, "_http_check", lambda *_a, **_kw: (False, "offline"))
    monkeypatch.setattr(doctor_module, "inspect_host_installations", lambda **_kw: [])

    report = doctor_module.run_doctor(config)

    assert any(check.name == "db" and check.status == "fail" for check in report.checks)
    assert not db_path.exists()


def test_parallel_provider_validation_contains_unexpected_worker_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = ProviderEntry(
        name="broken",
        type="ollama",
        model="model",
        base_url="http://127.0.0.1:11434",
    )
    monkeypatch.setattr(
        doctor_module,
        "validate_provider",
        lambda *_a, **_kw: (_ for _ in ()).throw(RuntimeError("secret")),
    )

    result = doctor_module._validate_provider_entries((provider,))

    assert result == [
        ProviderValidationResult(
            name="broken",
            provider_type="ollama",
            ok=False,
            usable=False,
            reason="provider validation failed unexpectedly",
        )
    ]


def test_openclaw_bridge_normalizes_invalid_attempt_without_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    observed: dict[str, Any] = {}

    class StoreStub:
        def has_finalization_action(
            self,
            _trace_id: str,
            _action: str,
            *,
            response_hash: str = "",
        ) -> bool:
            del response_hash
            return False

        def get_run(self, trace_id: str) -> dict[str, str]:
            return {
                "trace_id": trace_id,
                "session_id": "session",
                "status": "active",
            }

        def get_authoritative_finalization(
            self,
            _session_id: str,
            _trace_id: str,
            *,
            action: str = "",
            response_hash: str = "",
            policy_response_hash: str = "",
        ) -> None:
            del action, response_hash, policy_response_hash
            return None

        def record_finalization(self, **kwargs: Any) -> None:
            observed["finalization"] = kwargs

        def commit_terminal_finalization(self, **kwargs: Any) -> dict[str, Any]:
            observed["finalization"] = kwargs
            observed["closed"] = (
                kwargs["session_id"],
                kwargs["trace_id"],
                kwargs["status"],
            )
            return {
                "outcome": "committed",
                "authoritative": True,
                "action": kwargs["action"],
                "response_hash": kwargs["response_hash"],
                "status": kwargs["status"],
            }

        def close_turn_evidence(
            self,
            session_id: str,
            trace_id: str,
            *,
            status: str,
        ) -> None:
            observed["closed"] = (session_id, trace_id, status)

    class AdapterStub:
        store = StoreStub()

        def runtime_enabled(self) -> bool:
            return True

        def pre_verify_handler(self, **kwargs: Any) -> dict[str, int]:
            observed.update(kwargs)
            return {"evidence_revision": 7}

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", AdapterStub)

    result = node_bridge.handle(
        {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "trace",
            "attempt": "not-a-number",
            "finalResponse": "draft",
        }
    )

    assert result["action"] == "allow_pending"
    assert observed["attempt"] == 0
    assert result["evidenceRevision"] == 7
    assert "finalization" not in observed
    assert "closed" not in observed


def test_openclaw_pre_verify_exception_requires_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    class AdapterStub:
        def pre_verify_handler(self, **_kwargs: Any) -> None:
            raise OSError("database offline")

        def resolve_turn_trace(self, _session_id: str, trace_id: str) -> str:
            return trace_id

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", AdapterStub)

    result = node_bridge.handle(
        {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "trace",
            "finalResponse": "Parsed final response",
        }
    )

    assert result["action"] == "continue"
    assert "VERIFICATION UNAVAILABLE" in result["message"]


def test_openclaw_pre_verify_store_construction_failure_requires_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    class BrokenAdapter:
        def __init__(self) -> None:
            raise OSError("database offline")

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", BrokenAdapter)

    result = node_bridge.handle(
        {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "trace",
            "finalResponse": "Parsed final response",
        }
    )

    assert result["action"] == "continue"
    assert "VERIFICATION UNAVAILABLE" in result["message"]


def test_openclaw_enabled_accept_requires_evidence_revision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    store = Store(tmp_path / "missing-revision.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        host="openclaw",
        metadata={"request_kind": "trivial"},
    )

    class AdapterStub:
        def __init__(self) -> None:
            self.store = store

        def runtime_enabled(self) -> bool:
            return True

        def resolve_turn_trace(self, _session_id: str, trace_id: str) -> str:
            return trace_id

        def evaluate_completion_policy(
            self,
            _final_response: str,
            **_kwargs: Any,
        ) -> dict[str, str]:
            return {"action": "accept"}

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", AdapterStub)

    result = node_bridge.handle(
        {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "turn",
            "finalResponse": "draft",
        }
    )

    assert result["action"] == "continue"
    assert store.get_run("turn")["status"] == "active"
    assert store.get_authoritative_finalization("session", "turn") is None


def test_openclaw_soft_off_never_terminalizes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    class StoreSpy:
        def commit_terminal_finalization(self, **_kwargs: Any) -> None:
            raise AssertionError("soft-off must not commit")

    class AdapterStub:
        store = StoreSpy()

        def runtime_enabled(self) -> bool:
            return False

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", AdapterStub)

    assert node_bridge.handle(
        {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "turn",
            "finalResponse": "original",
        }
    ) == {"runtimeDisabled": True}


def test_openclaw_stale_evidence_cannot_terminalize(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge
    from agency_runtime.core.header.contract import fill_header_fields, format_header

    store = Store(tmp_path / "stale-revision.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        host="openclaw",
        metadata={"request_kind": "trivial"},
    )
    fields = fill_header_fields({}, "session", store, "", "turn")
    response = f"{format_header(fields)}\n\nDone."

    class MutatingAdapter(OpenClawAdapter):
        def evaluate_completion_policy(
            self,
            final_response: str,
            **kwargs: Any,
        ) -> dict[str, Any]:
            decision = super().evaluate_completion_policy(final_response, **kwargs)
            self.store.record_skill_loaded("session", "late-skill", trace_id="turn")
            return decision

    adapter = MutatingAdapter(store=store)
    monkeypatch.setattr(node_bridge, "OpenClawAdapter", lambda: adapter)

    result = node_bridge.handle(
        {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "turn",
            "finalResponse": response,
        }
    )

    assert result["action"] == "allow_pending"
    assert store.get_run("turn")["status"] == "active"
    assert store.get_authoritative_finalization("session", "turn") is None

    outbound = node_bridge.handle(
        {
            "action": "outbound_gate",
            "sessionId": "session",
            "traceId": "turn",
            "finalResponse": response,
        }
    )

    assert outbound["action"] == "replace"
    assert store.get_run("turn")["status"] == "active"
    assert store.get_authoritative_finalization("session", "turn") is None


def test_openclaw_concurrent_duplicate_callback_replays_one_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    store = Store(tmp_path / "concurrent-retry.db")
    store.create_run(
        trace_id="turn",
        session_id="session",
        host="openclaw",
        metadata={"request_kind": "trivial"},
    )
    barrier = threading.Barrier(2)

    class BarrierAdapter(OpenClawAdapter):
        def evaluate_completion_policy(
            self,
            final_response: str,
            **kwargs: Any,
        ) -> dict[str, Any]:
            decision = super().evaluate_completion_policy(final_response, **kwargs)
            barrier.wait(timeout=5)
            return decision

    adapter = BarrierAdapter(store=store)
    monkeypatch.setattr(node_bridge, "OpenClawAdapter", lambda: adapter)
    payload = {
        "action": "pre_verify",
        "sessionId": "session",
        "traceId": "turn",
        "finalResponse": "invalid",
    }

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(node_bridge.handle, (payload, payload)))

    assert {result["revisionId"] for result in results} == {results[0]["revisionId"]}
    assert store.get_run("turn")["status"] == "active"

    plain_adapter = OpenClawAdapter(store=store)
    monkeypatch.setattr(node_bridge, "OpenClawAdapter", lambda: plain_adapter)
    exhausted = node_bridge.handle({**payload, "finalResponse": "changed invalid"})

    assert exhausted["action"] == "terminal"
    assert exhausted["terminalRejected"] is True
    assert exhausted["terminalStatus"] == "retry_exhausted"
    assert "revisionId" not in exhausted
    assert store.get_run("turn")["status"] == "retry_exhausted"


def test_openclaw_bridge_main_fails_open_without_leaking_exception_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    class AdapterStub:
        def pre_llm_call_handler(self, **_kwargs: Any) -> None:
            raise RuntimeError("private bridge detail")

    monkeypatch.setattr(node_bridge, "OpenClawAdapter", AdapterStub)
    stdin = io.StringIO(json.dumps({"action": "preflight", "userMessage": "hello"}))
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    status = node_bridge.main()

    assert status == 0
    assert json.loads(stdout.getvalue()) == {}
    assert "host operation continues" in stderr.getvalue()
    assert "private bridge detail" not in stderr.getvalue()


def test_openclaw_bridge_main_fails_closed_for_unexpected_pre_verify_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    monkeypatch.setattr(
        node_bridge,
        "handle",
        lambda _payload: (_ for _ in ()).throw(RuntimeError("private verifier detail")),
    )
    stdin = io.StringIO(
        json.dumps(
            {
                "action": "pre_verify",
                "sessionId": "session",
                "traceId": "turn",
                "finalResponse": "draft",
            }
        )
    )
    stdout = io.StringIO()
    stderr = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    assert node_bridge.main() == 0
    assert json.loads(stdout.getvalue())["action"] == "continue"
    assert "response publication blocked" in stderr.getvalue()
    assert "private verifier detail" not in stderr.getvalue()


def test_openclaw_bridge_main_never_emits_nonfinite_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.adapters.openclaw import node_bridge

    monkeypatch.setattr(node_bridge, "_read_payload", lambda: {"action": "test"})
    monkeypatch.setattr(node_bridge, "handle", lambda _payload: {"value": float("nan")})
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdout", stdout)

    assert node_bridge.main() == 0
    assert stdout.getvalue() == "{}\n"


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), 601])
def test_canary_rejects_unbounded_timeouts(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout must be"):
        run_canary("codex", timeout=timeout)


def test_canary_inspection_failure_becomes_readiness_evidence(tmp_path: Path) -> None:
    def fail(_host: str) -> dict[str, Any]:
        raise OSError("private path")

    report = run_canary(
        "codex",
        db_path=tmp_path / "absent.db",
        inspector=fail,
    )

    assert report["ready"] is False
    assert report["native"]["inspection_error"] == "native inspection unavailable"
    assert "private path" not in json.dumps(report)


def test_canary_rejects_a_non_mapping_backend_result(tmp_path: Path) -> None:
    db_path = tmp_path / "agency.db"
    Store(db_path)
    native = {
        "host": "codex",
        "executable_discovered": True,
        "host_version": "1.0.0",
        "install_id": "install-1",
        "bundle_digest": "a" * 64,
    }

    class Backend:
        def execute(self, **_kwargs: Any) -> list[str]:
            return ["invalid"]

    report = run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=db_path,
        inspector=lambda _host: native,
        backend_factory=lambda *_a, **_kw: Backend(),
    )

    assert report["live_attempted"] is True
    assert report["canary_passed"] is False
    assert "safe host invocation failed" in report["unmet_prerequisites"][-1]


def test_codex_inventory_requires_an_exact_agency_plugin_identity() -> None:
    assert _codex_isolated_plugin_enabled(
        {
            "pluginId": "agency-preflight@agency-runtime",
            "installed": True,
            "enabled": True,
        }
    )
    assert not _codex_isolated_plugin_enabled(
        {
            "pluginId": "agency-preflight-malicious",
            "installed": True,
            "enabled": True,
        }
    )


def test_canary_auth_copy_rejects_oversized_input(tmp_path: Path) -> None:
    source = tmp_path / "auth.json"
    source.write_bytes(b"x" * (1024 * 1024 + 1))

    with pytest.raises(ValueError, match="exceeds the safety limit"):
        _copy_bounded_auth(source, tmp_path / "isolated" / "auth.json", host="Codex")


def test_canary_auth_copy_hardens_empty_destination_before_writing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from agency_runtime.core import configuration

    source = tmp_path / "source-auth.json"
    source.write_bytes(b'{"token":"secret"}')
    destination = tmp_path / "isolated" / "auth.json"
    events: list[tuple[str, int | None]] = []
    monkeypatch.setattr(
        configuration,
        "restrict_private_directory",
        lambda _path: events.append(("directory", None)),
    )
    monkeypatch.setattr(
        configuration,
        "restrict_private_file",
        lambda path: events.append(("file", Path(path).stat().st_size)),
    )

    _copy_bounded_auth(source, destination, host="Codex")

    assert events == [
        ("directory", None),
        ("file", 0),
        ("file", len(b'{"token":"secret"}')),
    ]
