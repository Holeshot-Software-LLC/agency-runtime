"""Regression coverage for host discovery, hooks, diagnostics, and canaries."""

from __future__ import annotations

import io
import json
import sys
import threading
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
        def record_finalization(self, **kwargs: Any) -> None:
            observed["finalization"] = kwargs

    class AdapterStub:
        store = StoreStub()

        def runtime_enabled(self) -> bool:
            return True

        def pre_verify_handler(self, **kwargs: Any) -> None:
            observed.update(kwargs)

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

    assert result is None or result == {}
    assert observed["attempt"] == 0
    assert observed["finalization"]["trace_id"] == "trace"


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
