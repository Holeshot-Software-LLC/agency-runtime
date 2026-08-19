from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.core import canary
from agency_runtime.core.codex_global_guidance import render_codex_global_guidance
from agency_runtime.core.store.sqlite import Store


def _process_result() -> SimpleNamespace:
    return SimpleNamespace(
        returncode=0,
        timed_out=False,
        stdout="{}",
        stderr="",
        stdout_truncated=False,
        stderr_truncated=False,
    )


def test_codex_setup_inventory_and_execution_share_one_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    now = {"value": 0.0}
    timeouts: list[float] = []

    def runner(_argv: list[str], **kwargs: Any) -> SimpleNamespace:
        timeout = float(kwargs["timeout"])
        timeouts.append(timeout)
        now["value"] += min(6.0, timeout)
        return _process_result()

    monkeypatch.setattr(canary.time, "monotonic", lambda: now["value"])
    monkeypatch.setattr(
        canary,
        "_prepare_private_host_home",
        lambda runtime_home, **_kwargs: runtime_home / "codex",
    )
    monkeypatch.setattr(canary, "_isolated_canary_environment", lambda *_args: {})
    backend = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=10.0,
        marketplace=tmp_path / "marketplace",
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={},
    )

    result = backend.execute(task="nonce-bound canary", workdir=str(tmp_path))

    assert result["status"] == "timed_out"
    assert result["exit_code"] == 124
    assert timeouts == [10.0, 4.0]


def test_codex_setup_and_model_execution_refuse_an_exhausted_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    now = {"value": 0.0}
    invoked = False

    def runner(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        nonlocal invoked
        invoked = True
        return _process_result()

    monkeypatch.setattr(canary.time, "monotonic", lambda: now["value"])
    backend = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=10.0,
        marketplace=tmp_path / "marketplace",
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={},
    )
    assert (
        backend._install_plugin(workdir=str(tmp_path), env={}, deadline=0.0)["status"]
        == "timed_out"
    )
    assert invoked is False

    monkeypatch.setattr(
        canary,
        "_prepare_private_host_home",
        lambda runtime_home, **_kwargs: runtime_home / "codex",
    )
    monkeypatch.setattr(canary, "_isolated_canary_environment", lambda *_args: {})
    monkeypatch.setattr(
        canary._SafeCodexCanaryBackend,
        "_install_plugin",
        lambda _self, **_kwargs: None,
    )

    def consume_deadline(_self: Any, **_kwargs: Any) -> None:
        now["value"] = 10.0

    monkeypatch.setattr(canary._SafeCodexCanaryBackend, "_verify_plugin", consume_deadline)
    result = backend.execute(task="nonce-bound canary", workdir=str(tmp_path))
    assert result["status"] == "timed_out"
    assert invoked is False


def test_isolated_codex_activation_canary_marks_existing_store_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def runner(_argv: list[str], **kwargs: Any) -> SimpleNamespace:
        calls.append(kwargs)
        return _process_result()

    monkeypatch.setattr(
        canary,
        "_prepare_private_host_home",
        lambda runtime_home, **_kwargs: runtime_home / "codex",
    )
    monkeypatch.setattr(canary, "_isolated_canary_environment", lambda *_args: {})
    monkeypatch.setattr(
        canary,
        "_project_isolated_runtime_control",
        lambda *_args, **_kwargs: {"enabled": True},
    )
    monkeypatch.setattr(
        canary._SafeCodexCanaryBackend,
        "_install_plugin",
        lambda _self, **_kwargs: None,
    )
    monkeypatch.setattr(
        canary._SafeCodexCanaryBackend,
        "_verify_plugin",
        lambda _self, **_kwargs: None,
    )
    backend = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=10.0,
        marketplace=tmp_path / "marketplace",
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={},
        require_exact_activation_rollout=True,
    )

    backend.execute(task="nonce-bound canary", workdir=str(tmp_path))

    assert calls[-1]["env"]["AGENCY_CANARY_REQUIRE_EXISTING_STORE"] == "1"


def test_isolated_codex_product_profile_projects_exact_global_guidance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed: list[str] = []

    def prepare(runtime_home: Path, **_kwargs: Any) -> Path:
        codex_home = runtime_home / "codex"
        codex_home.mkdir()
        return codex_home

    def runner(_argv: list[str], **kwargs: Any) -> SimpleNamespace:
        codex_home = Path(kwargs["env"]["CODEX_HOME"])
        observed.append((codex_home / "AGENTS.md").read_text(encoding="utf-8"))
        return _process_result()

    monkeypatch.setattr(canary, "_prepare_private_host_home", prepare)
    monkeypatch.setattr(canary, "_isolated_canary_environment", lambda *_args: {})
    monkeypatch.setattr(
        canary,
        "_project_isolated_runtime_control",
        lambda *_args, **_kwargs: {"enabled": True},
    )
    monkeypatch.setattr(
        canary._SafeCodexCanaryBackend,
        "_install_plugin",
        lambda _self, **_kwargs: None,
    )
    monkeypatch.setattr(
        canary._SafeCodexCanaryBackend,
        "_verify_plugin",
        lambda _self, **_kwargs: None,
    )
    guidance = render_codex_global_guidance()
    backend = canary._SafeCodexCanaryBackend(
        executable="codex",
        db_path=tmp_path / "agency.db",
        timeout=10.0,
        marketplace=tmp_path / "marketplace",
        auth_source=tmp_path / "auth.json",
        process_runner=runner,
        source_env={},
        project_agency_global_guidance=True,
    )

    backend.execute(task="product request", workdir=str(tmp_path))

    assert observed == [guidance]


def test_claude_auth_preparation_consumes_the_same_execution_budget(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    now = {"value": 0.0}
    invoked = False

    def prepare(runtime_home: Path, **_kwargs: Any) -> Path:
        now["value"] = 5.0
        return runtime_home / "claude"

    def runner(*_args: Any, **_kwargs: Any) -> SimpleNamespace:
        nonlocal invoked
        invoked = True
        return _process_result()

    monkeypatch.setattr(canary.time, "monotonic", lambda: now["value"])
    monkeypatch.setattr(canary, "_prepare_private_host_home", prepare)
    monkeypatch.setattr(canary, "_isolated_canary_environment", lambda *_args: {})
    backend = canary._SafeClaudeCanaryBackend(
        executable="claude",
        db_path=tmp_path / "agency.db",
        timeout=5.0,
        plugin_dir=tmp_path / "plugin",
        auth_source=tmp_path / "credentials.json",
        process_runner=runner,
        source_env={},
    )

    result = backend.execute(task="nonce-bound canary", workdir=str(tmp_path))

    assert result["status"] == "timed_out"
    assert result["exit_code"] == 124
    assert invoked is False


def test_claude_canary_projects_a_cross_provider_codex_auth_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    prepared: list[tuple[str, Path]] = []
    observed_env: dict[str, str] = {}

    def prepare(runtime_home: Path, **kwargs: Any) -> Path:
        home = runtime_home / str(kwargs["directory_name"])
        home.mkdir()
        prepared.append((str(kwargs["directory_name"]), Path(kwargs["auth_source"])))
        return home

    def runner(*_args: Any, **kwargs: Any) -> SimpleNamespace:
        observed_env.update(kwargs["env"])
        return _process_result()

    monkeypatch.setattr(canary, "_prepare_private_host_home", prepare)
    monkeypatch.setattr(canary, "_isolated_canary_environment", lambda *_args: {})
    monkeypatch.setattr(
        canary,
        "_project_isolated_runtime_control",
        lambda *_args, **_kwargs: {"enabled": True},
    )
    backend = canary._SafeClaudeCanaryBackend(
        executable="claude",
        db_path=tmp_path / "agency.db",
        timeout=5.0,
        plugin_dir=tmp_path / "plugin",
        auth_source=tmp_path / "claude" / ".credentials.json",
        process_runner=runner,
        source_env={},
        child_judge_provider="codex-subscription",
        child_judge_transport="codex",
        child_judge_auth_source=tmp_path / "codex" / "auth.json",
    )

    result = backend.execute(task="nonce-bound canary", workdir=str(tmp_path))

    assert observed_env["AGENCY_CANARY_CHILD_JUDGE_PROVIDER"] == "codex-subscription"
    assert Path(observed_env["CLAUDE_CONFIG_DIR"]).name == "claude"
    assert Path(observed_env["CODEX_HOME"]).name == "child-judge-codex"
    assert prepared == [
        ("claude", tmp_path / "claude" / ".credentials.json"),
        ("child-judge-codex", tmp_path / "codex" / "auth.json"),
    ]
    assert result["child_judge_provider_requested"] == "codex-subscription"


def _ready_native(*, install_id: str) -> dict[str, Any]:
    return {
        "host": "codex",
        "executable_discovered": True,
        "host_version": "codex 1.0.0",
        "install_id": install_id,
        "bundle_digest": "a" * 64,
    }


def test_changed_install_lineage_cannot_receive_a_stale_attestation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "agency.db"
    store = Store(path)
    inspected = iter([_ready_native(install_id="before"), _ready_native(install_id="after")])

    monkeypatch.setattr(
        canary,
        "_prepare_live_invocation",
        lambda *_args, **_kwargs: canary._LivePreparation(
            store=store,
            before={},
            backend=object(),
            prompt="nonce-bound prompt",
            expected_query_hash="hash",
        ),
    )
    monkeypatch.setattr(
        canary,
        "_invoke_and_collect_evidence",
        lambda *_args, **_kwargs: canary._InvocationOutcome(
            result={},
            evidence={"accepted_trace_ids": ["trace"]},
        ),
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: canary._CanaryProof(
            invocation={"status": "completed"},
            result_scope="isolated-profile",
            passed=True,
            failures=(),
        ),
    )
    monkeypatch.setattr(
        canary,
        "_persist_attestation",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("stale lineage reached attestation persistence")
        ),
    )

    report = canary.run_canary(
        "codex",
        execute=True,
        confirm="RUN LIVE codex CANARY",
        db_path=path,
        inspector=lambda _host: next(inspected),
        backend_factory=lambda *_args, **_kwargs: object(),
    )

    assert report["live_attempted"] is True
    assert report["canary_passed"] is False
    assert report["attestation_persisted"] is False
    assert report["unmet_prerequisites"] == [
        "native host or managed bundle identity changed or became unverified during canary"
    ]


def test_attestation_recheck_rejects_new_readiness_failure(tmp_path: Path) -> None:
    before = canary._assess_readiness(
        "codex",
        tmp_path / "missing.db",
        lambda _host: _ready_native(install_id="stable"),
    )
    after = replace(before, unmet=("host became unready",))

    assert canary._attestation_identity_is_current(before, after) is False
