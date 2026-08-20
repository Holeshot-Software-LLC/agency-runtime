"""Bounded Claude accepted-outcome canary orchestration and CLI-safe proof."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from agency_runtime.cli.main import build_parser
from agency_runtime.core import canary, canary_backends
from agency_runtime.core import child_delivery_evidence as child_evidence
from agency_runtime.core import outcome_canary as subject
from agency_runtime.core.accepted_outcome_canary_contract import (
    ACCEPTED_OUTCOME_CONFIRMATION,
    ACCEPTED_OUTCOME_CONTRACTOR_SLUG,
    build_accepted_outcome_canary_prompt,
)
from agency_runtime.core.canary_parent_recruiter_provider import (
    ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV,
)
from agency_runtime.core.child_delivery_evidence import _HostAcceptedOutcomeCollection
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.workforce.inference import _explicit_indivisible_unit_request

PAIR_ID = "7" * 32
PRODUCER_DECISION = "producer-decision"
VERIFIER_DECISION = "verifier-decision"
PROVIDER = "codex-subscription"
PRODUCER_DIGEST = "a" * 64


def _native(_host: str) -> dict[str, object]:
    return {
        "host": "claude",
        "executable_discovered": True,
        "registered": True,
        "enabled": True,
        "host_version": "claude 1.0",
        "install_id": "install-1",
        "bundle_digest": "b" * 64,
    }


def _control() -> dict[str, object]:
    return {
        "schema_version": "agency.runtime_control.v1",
        "enabled": True,
        "generation": 4,
        "updated_at": "2026-08-20T00:00:00Z",
        "source": "test",
    }


def _set_master(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(canary, "_read_canary_master_control", lambda: (_control(), "direct"))


def _card(slug: str) -> dict[str, object]:
    return {
        "specialist_slug": slug,
        "specialist_version": "1.0.0",
        "specialist_prompt_hash": "c" * 64,
        "body_character_length": 120,
    }


class _Store:
    def __init__(self, *, provider: str = PROVIDER) -> None:
        self.provider = provider

    def get_workforce_worker(self, slug: str) -> dict[str, object]:
        assert slug == ACCEPTED_OUTCOME_CONTRACTOR_SLUG
        return {
            "worker_id": "worker-typescript",
            "agent_slug": slug,
            "employment_class": "contractor",
            "enabled": True,
        }

    def get_native_child_staffing_decision(self, decision_id: str) -> dict[str, object]:
        producer = decision_id == PRODUCER_DECISION
        child_id = "producer-child" if producer else "verifier-child"
        return {
            "decision_id": decision_id,
            "host": "claude",
            "parent_session_id": "parent-session",
            "parent_trace_id": "parent-trace",
            "launch_id": "producer-launch" if producer else "verifier-launch",
            "binding_kind": "child_id",
            "binding_id": child_id,
            "nonce": "producer-nonce" if producer else "verifier-nonce",
            "provider_receipt_digest": "d" * 64,
            "provider_attempts": [
                {
                    "provider_name": self.provider,
                    "status": "applied",
                }
            ],
            "cards": [_card(ACCEPTED_OUTCOME_CONTRACTOR_SLUG if producer else "code-reviewer")],
        }

    def get_native_child_delivery_verification(self, decision_id: str) -> dict[str, object]:
        producer = decision_id == PRODUCER_DECISION
        child_id = "producer-child" if producer else "verifier-child"
        return {
            "decision_id": decision_id,
            "host": "claude",
            "parent_session_id": "parent-session",
            "parent_trace_id": "parent-trace",
            "launch_id": "producer-launch" if producer else "verifier-launch",
            "binding_kind": "child_id",
            "binding_id": child_id,
            "child_id": child_id,
            "nonce": "producer-nonce" if producer else "verifier-nonce",
            "artifact_digest": PRODUCER_DIGEST if producer else "e" * 64,
            "verified_delivery": True,
        }


def _accepted_collection(*, promoted: bool = False) -> _HostAcceptedOutcomeCollection:
    return _HostAcceptedOutcomeCollection(
        result={
            "recorded": True,
            "promoted": promoted,
            "reason": "accepted",
            "event_id": "event-1",
            "worker_id": "worker-typescript",
            "accepted_outcome_key": "f" * 64,
            "artifact_digest": PRODUCER_DIGEST,
        },
        reason="accepted",
        pair_id=PAIR_ID,
        producer_decision_id=PRODUCER_DECISION,
        verifier_decision_id=VERIFIER_DECISION,
    )


class _Backend:
    child_judge_provider = PROVIDER
    parent_recruiter_provider = PROVIDER

    def __init__(self, collection: _HostAcceptedOutcomeCollection | None) -> None:
        self.collection = collection
        self.calls = 0

    def execute_with_accepted_outcome(self, **_kwargs: object):
        self.calls += 1
        reason = self.collection.reason if self.collection is not None else "provider_pin_mismatch"
        return (
            {
                "backend": "claude",
                "profile_scope": "isolated-profile",
                "status": "completed",
                "exit_code": 0,
                "stdout_truncated": False,
                "stderr_truncated": False,
                "output": "secret child and model text must not escape",
                "child_judge_provider_requested": PROVIDER,
                "parent_recruiter_provider_requested": PROVIDER,
                "host_accepted_outcome_reason": reason,
            },
            self.collection,
        )


def _prepare(
    monkeypatch: pytest.MonkeyPatch,
    *,
    store: _Store,
    backend: _Backend,
) -> None:
    monkeypatch.setattr(subject.secrets, "token_hex", lambda _size: PAIR_ID)

    def prepare(_host: str, **kwargs: object) -> canary._LivePreparation:
        prompt = str(kwargs["base_prompt"])
        assert prompt == build_accepted_outcome_canary_prompt(PAIR_ID)
        return canary._LivePreparation(
            store=store,
            before={},
            backend=backend,
            prompt=prompt + "\n\nCanary nonce: nonce",
            expected_query_hash="9" * 64,
        )

    monkeypatch.setattr(canary, "_prepare_live_invocation", prepare)


def test_pair_prompt_is_exactly_two_serial_children_with_bound_roles() -> None:
    prompt = build_accepted_outcome_canary_prompt(PAIR_ID)

    assert _explicit_indivisible_unit_request(prompt) is True
    assert "Agent tool exactly twice, serially" in prompt
    assert prompt.count(f"agency-accepted-outcome-pair:v1:{PAIR_ID}:producer") == 1
    assert prompt.count(f"agency-accepted-outcome-pair:v1:{PAIR_ID}:verifier") == 1
    assert prompt.count('"schema":"agency.verifier-semantic.v1"') == 2
    assert "complete response copied verbatim" in prompt


def test_primary_cli_parser_exposes_explicit_outcome_mode() -> None:
    parsed = build_parser().parse_args(
        ["host-canary", "claude", "--accepted-outcome", "--timeout", "420"]
    )

    assert parsed.accepted_outcome is True
    assert parsed.timeout == 420


def test_live_preparation_preserves_custom_pair_prompt_and_appends_nonce(
    tmp_path: Path,
) -> None:
    backend = SimpleNamespace()
    prepared = canary._prepare_live_invocation(
        "claude",
        path=tmp_path / "agency.db",
        timeout=10,
        native=_native("claude"),
        backend_factory=lambda *_args, **_kwargs: backend,
        base_prompt="custom accepted-outcome pair",
    )

    assert prepared.error is None
    assert prepared.backend is backend
    assert prepared.prompt is not None
    assert prepared.prompt.startswith("custom accepted-outcome pair\n\nCanary nonce: ")
    assert len(prepared.prompt.rsplit(" ", 1)[-1]) == 32


def test_readiness_and_wrong_confirmation_never_prepare_or_execute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch)
    monkeypatch.setattr(
        canary,
        "_prepare_live_invocation",
        lambda *_args, **_kwargs: pytest.fail("preparation must remain behind confirmation"),
    )
    ready = subject.run_accepted_outcome_canary(
        "claude",
        db_path=tmp_path / "absent.db",
        inspector=_native,
    )
    refused = subject.run_accepted_outcome_canary(
        "claude",
        execute=True,
        confirm="RUN LIVE claude CANARY",
        db_path=tmp_path / "absent.db",
        inspector=_native,
    )

    assert ready["schema_version"] == "agency.accepted_outcome_canary.v1"
    assert ready["ready"] is True
    assert ready["execute_confirmation"] == ACCEPTED_OUTCOME_CONFIRMATION
    assert ready["live_attempted"] is False
    assert refused["live_attempted"] is False
    assert ACCEPTED_OUTCOME_CONFIRMATION in refused["unmet_prerequisites"][-1]


def test_success_reports_both_actual_providers_and_no_model_text(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch)
    backend = _Backend(_accepted_collection(promoted=True))
    _prepare(monkeypatch, store=_Store(), backend=backend)

    report = subject.run_accepted_outcome_canary(
        "claude",
        execute=True,
        confirm=ACCEPTED_OUTCOME_CONFIRMATION,
        db_path=tmp_path / "agency.db",
        timeout=420,
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: backend,
    )

    assert report["canary_passed"] is True
    assert report["promotion_observed"] is True
    assert report["child_judge_provider_requested"] == PROVIDER
    assert report["parent_recruiter_provider_requested"] == PROVIDER
    assert report["child_judge_provider_answered"] == {
        "producer": PROVIDER,
        "verifier": PROVIDER,
    }
    assert report["producer"]["cards"][0]["specialist_slug"] == (ACCEPTED_OUTCOME_CONTRACTOR_SLUG)
    assert report["verifier"]["cards"][0]["specialist_slug"] == "code-reviewer"
    assert report["accepted_outcome"]["recorded"] is True
    assert report["invocation"]["host_accepted_outcome_reason"] == "accepted"
    assert report["invocation"]["parent_recruiter_provider_requested"] == PROVIDER
    assert "output" not in report["invocation"]
    assert "secret child" not in json.dumps(report)
    assert backend.calls == 1


def test_collector_refusal_is_named_and_cannot_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_master(monkeypatch)
    backend = _Backend(_HostAcceptedOutcomeCollection(result=None, reason="provider_pin_mismatch"))
    _prepare(monkeypatch, store=_Store(), backend=backend)

    report = subject.run_accepted_outcome_canary(
        "claude",
        execute=True,
        confirm=ACCEPTED_OUTCOME_CONFIRMATION,
        db_path=tmp_path / "agency.db",
        inspector=_native,
        backend_factory=lambda *_args, **_kwargs: backend,
    )

    assert report["canary_passed"] is False
    assert "(provider_pin_mismatch)" in report["unmet_prerequisites"][-1]


@pytest.mark.parametrize(
    ("host", "mode", "profile_scope", "require_existing_store"),
    [
        ("zcode", "agency", "isolated-profile", False),
        ("claude", "native-only", "isolated-profile", False),
        ("claude", "agency", "current-profile", False),
        ("claude", "agency", "isolated-profile", True),
    ],
)
def test_unsupported_scope_is_rejected_before_inspection(
    host: str,
    mode: str,
    profile_scope: str,
    require_existing_store: bool,
) -> None:
    with pytest.raises(ValueError):
        subject.run_accepted_outcome_canary(
            host,
            mode=mode,
            profile_scope=profile_scope,
            require_existing_store=require_existing_store,
            inspector=lambda _host: pytest.fail("invalid scope reached native inspection"),
        )


def test_safe_backend_collects_pair_before_private_home_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    auth = tmp_path / "credentials.json"
    auth.write_text("{}", encoding="utf-8")
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    owner_home = tmp_path / "owner"
    owner_home.mkdir()
    observed: dict[str, Any] = {}
    sentinel = _HostAcceptedOutcomeCollection(result=None, reason="verdict_rejected")
    monkeypatch.setattr(child_evidence, "storage_parent_is_trusted", lambda *_a, **_k: True)

    def collect(collection, **kwargs):
        observed["root"] = collection.root
        observed["root_alive"] = collection.root.is_dir()
        observed["expected_provider"] = kwargs["expected_provider"]
        return sentinel

    monkeypatch.setattr(canary_backends, "_collect_private_host_accepted_outcome", collect)

    def runner(argv: list[str], **kwargs: object) -> BoundedProcessResult:
        observed["argv"] = argv
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        observed["parent_recruiter_provider"] = environment[
            ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER_ENV
        ]
        observed["codex_home"] = Path(environment["CODEX_HOME"])
        return BoundedProcessResult(0, json.dumps({"result": "done"}), "")

    backend = canary_backends.SafeClaudeCanaryBackend(
        executable="claude",
        db_path=tmp_path / "agency.db",
        timeout=10,
        plugin_dir=plugin,
        auth_source=auth,
        process_runner=runner,
        source_env={"HOME": str(owner_home), "USERPROFILE": str(owner_home)},
        child_judge_provider=PROVIDER,
        child_judge_transport="",
        parent_recruiter_provider=PROVIDER,
        parent_recruiter_transport="codex",
        parent_recruiter_auth_source=auth,
    )
    record, collection = backend.execute_with_accepted_outcome(
        task="bounded pair",
        workdir=str(tmp_path),
        store=SimpleNamespace(),
    )

    assert collection is sentinel
    assert record["host_accepted_outcome_reason"] == "verdict_rejected"
    assert observed["root_alive"] is True
    assert not observed["root"].exists()
    assert observed["expected_provider"] == PROVIDER
    assert observed["parent_recruiter_provider"] == PROVIDER
    assert not observed["codex_home"].exists()
    assert record["parent_recruiter_provider_requested"] == PROVIDER
    argv = observed["argv"]
    assert argv[argv.index("--max-turns") + 1] == "4"
    assert "--tools=Agent" in argv
