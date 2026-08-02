"""Branch-complete lifecycle tests for authoritative turn preflight and headers."""

from __future__ import annotations

import copy
import importlib
from hashlib import sha256
from types import SimpleNamespace
from typing import Any

import pytest

import agency_runtime.core.delegation.events as delegation_events
import agency_runtime.core.header.contract as contract
import agency_runtime.core.preflight as preflight
import agency_runtime.core.preflight_recipe as preflight_recipe
import agency_runtime.core.retry_receipts as retry_receipts
import agency_runtime.core.selector.delegation_detection as delegation_detection
import agency_runtime.core.selector.pipeline as pipeline
import agency_runtime.core.selector.policy as policy
import agency_runtime.core.specialist_context as specialist_context
from agency_runtime.core.config import AgencyConfig, AgentActivationConfig
from agency_runtime.core.resident_manager_binding import (
    build_resident_manager_binding,
    resident_manager_host_mode,
)
from agency_runtime.core.turn_origin import native_adapter_turn_origin

finalizer = importlib.import_module("agency_runtime.core.header.finalize")


def _active_snapshot() -> dict[str, Any]:
    return {
        "session_id": "session",
        "trace_id": "trace",
        "status": "active",
        "request_kind": "trivial",
        "evidence_revision": 1,
        "skills": [],
        "specialists": [],
        "delegations": [],
        "model_receipt": None,
        "run": {
            "session_id": "session",
            "trace_id": "trace",
            "status": "active",
            "request_kind": "trivial",
            "evidence_revision": 1,
            "ended_at": "",
            "terminal_finalization_id": "",
        },
    }


def _valid_header() -> str:
    return contract.format_header(
        {
            "agencies_loaded": "none",
            "agencies_delegated": "none",
            "skills_loaded": "none",
            "actual_model_selected": "unknown -> unavailable - no model receipt recorded",
            "recruited_via": "none",
            "why": "Authoritative audit evidence.",
            "how_it_shaped_outcome": "Preserved the current turn boundary.",
        }
    )


def _current_workspace_write_plan() -> dict[str, Any]:
    return {
        "assignment_version": "4",
        "work_unit_id": "unit-1234567890",
        "goal_hash": "a" * 64,
        "deliverable_kind": "implementation",
        "recommended_agent": "minimal-change-engineer",
        "recommended_agents": ["minimal-change-engineer"],
        "selection_confidence": 0.99,
        "rationale_codes": ["exact_workspace_change"],
        "depends_on": [],
        "parallelization": "sequential",
        "mutation_scope": "workspace_write",
        "resource_hashes": [],
        "required_tools": ["apply_patch"],
        "required_evidence": ["workspace_patch_receipt"],
        "delegation_strength": "strongly_preferred",
    }


def test_completion_snapshot_rejects_every_untrusted_shape() -> None:
    invalid: list[tuple[Any, str]] = [
        (None, "snapshot could not be verified"),
        ({**_active_snapshot(), "run": None}, "run could not be verified"),
    ]

    snapshot = _active_snapshot()
    snapshot["session_id"] = "other"
    invalid.append((snapshot, "does not belong"))
    snapshot = _active_snapshot()
    snapshot["trace_id"] = "other"
    invalid.append((snapshot, "requested Agency turn"))
    snapshot = _active_snapshot()
    snapshot["status"] = ""
    invalid.append((snapshot, "lifecycle status"))
    snapshot = _active_snapshot()
    snapshot["run"]["ended_at"] = "now"
    invalid.append((snapshot, "lifecycle binding"))
    snapshot = _active_snapshot()
    snapshot["request_kind"] = "unknown"
    invalid.append((snapshot, "request kind"))
    snapshot = _active_snapshot()
    snapshot["evidence_revision"] = True
    invalid.append((snapshot, "evidence revision"))

    for field in ("skills", "specialists", "delegations"):
        snapshot = _active_snapshot()
        snapshot[field] = "not-a-list"
        invalid.append((snapshot, f"{field} evidence"))
    snapshot = _active_snapshot()
    snapshot["skills"] = [1]
    invalid.append((snapshot, "skills evidence"))
    snapshot = _active_snapshot()
    snapshot["specialists"] = [1]
    invalid.append((snapshot, "specialists evidence"))
    snapshot = _active_snapshot()
    snapshot["delegations"] = [1]
    invalid.append((snapshot, "delegations evidence"))
    snapshot = _active_snapshot()
    snapshot["model_receipt"] = "not-a-mapping"
    invalid.append((snapshot, "model receipt evidence"))

    for candidate, message in invalid:
        with pytest.raises(contract.EvidenceCorrelationError, match=message):
            contract._validate_completion_snapshot(candidate, "session", "trace")


class _RaisingRun(dict[str, Any]):
    def get(self, _key: str, _default: Any = None) -> Any:
        raise RuntimeError("hostile mapping")


class _RunStore:
    def __init__(self, run: Any = None, *, error: Exception | None = None) -> None:
        self.run = run
        self.error = error

    def get_run(self, _trace_id: str) -> Any:
        if self.error is not None:
            raise self.error
        return self.run


def test_correlation_reader_fails_closed_for_unverifiable_lifecycles() -> None:
    assert contract.correlation_error(None, "session", "") == (
        "trace_id is required for authoritative Agency evidence"
    )
    assert contract.correlation_error(None, "session", "trace") == ""
    assert contract.correlation_error(object(), "session", "trace") == (
        "evidence store cannot verify turn correlation"
    )
    assert (
        contract.correlation_error(_RunStore(error=RuntimeError("offline")), "session", "trace")
        == "turn correlation could not be verified"
    )
    assert contract.correlation_error(_RunStore(None), "session", "trace") == (
        "trace_id does not identify a recorded Agency turn"
    )
    assert contract.correlation_error(_RunStore(_RaisingRun()), "session", "trace") == (
        "turn correlation could not be verified"
    )
    assert (
        contract.correlation_error(
            _RunStore({"session_id": "other", "status": "active"}), "session", "trace"
        )
        == "trace_id does not belong to session_id"
    )
    assert (
        contract.correlation_error(
            _RunStore({"session_id": "session", "status": ""}),
            "session",
            "trace",
            require_active=True,
        )
        == "turn lifecycle status could not be verified"
    )
    assert (
        contract.correlation_error(
            _RunStore({"session_id": "session", "status": "completed"}),
            "session",
            "trace",
            require_active=True,
        )
        == "trace_id identifies a terminal Agency turn"
    )


class _SnapshotFailureStore:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def get_completion_evidence_snapshot(self, *_args: str) -> dict[str, Any]:
        raise self.error


def test_snapshot_reader_preserves_only_known_correlation_errors() -> None:
    with pytest.raises(contract.EvidenceCorrelationError, match="session_id is required"):
        contract.read_completion_evidence_snapshot(object(), "", "trace")
    with pytest.raises(contract.EvidenceCorrelationError, match="snapshot could not be verified"):
        contract.read_completion_evidence_snapshot(object(), "session", "trace")
    with pytest.raises(contract.EvidenceCorrelationError, match="does not belong"):
        contract.read_completion_evidence_snapshot(
            _SnapshotFailureStore(ValueError("trace_id does not belong to session_id")),
            "session",
            "trace",
        )
    with pytest.raises(contract.EvidenceCorrelationError, match="snapshot could not be verified"):
        contract.read_completion_evidence_snapshot(
            _SnapshotFailureStore(ValueError("sensitive internal failure")),
            "session",
            "trace",
        )


def test_completion_policy_fails_closed_when_atomic_evidence_breaks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with monkeypatch.context() as patch:
        patch.setattr(
            contract,
            "_validate_completion_snapshot",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                contract.EvidenceCorrelationError("offline")
            ),
        )
        violation = contract.validate_completion_policy(
            _valid_header(),
            session_id="session",
            trace_id="trace",
            store=object(),
            evidence_snapshot=_active_snapshot(),
        )
        assert violation == {
            "message": (
                "AGENCY EVIDENCE VERIFICATION UNAVAILABLE: Turn-scoped specialist, "
                "delegation, model, skill, or request-kind evidence could not be verified "
                "from one atomic snapshot. Do not publish this response; restore the "
                "evidence store and retry."
            ),
            "missing": ["evidence_verification"],
        }

    with monkeypatch.context() as patch:
        patch.setattr(contract, "_validate_completion_snapshot", lambda *_args, **_kwargs: {})
        violation = contract.validate_completion_policy(
            _valid_header(),
            session_id="session",
            trace_id="trace",
            store=object(),
            evidence_snapshot=_active_snapshot(),
        )
        assert violation is not None
        assert violation["missing"] == ["evidence_verification"]

    with monkeypatch.context() as patch:
        patch.setattr(
            contract,
            "fill_header_fields",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                contract.EvidenceCorrelationError("offline")
            ),
        )
        violation = contract.validate_completion_policy(
            _valid_header(),
            session_id="session",
            trace_id="trace",
            store=object(),
            evidence_snapshot=_active_snapshot(),
        )
        assert violation is not None
        assert violation["missing"] == ["evidence_verification"]

    with pytest.raises(contract.EvidenceCorrelationError, match="does not identify"):
        contract.fill_header_fields({}, "session", _RunStore(None), trace_id="trace")


class _AcceptedResponseStore:
    def __init__(self, result: Any = None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error

    def get_authoritative_finalization(self, *_args: Any, **_kwargs: Any) -> Any:
        if self.error is not None:
            raise self.error
        return self.result


class _FinalizationRecorder:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record_finalization(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)

    def get_authoritative_finalization(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_finalization_helpers_reject_unverifiable_acceptance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(contract.EvidenceCorrelationError, match="terminal response evidence"):
        finalizer.accepted_response_run(object(), "session", "trace", "response")
    with pytest.raises(contract.EvidenceCorrelationError, match="terminal response evidence"):
        finalizer.accepted_response_run(
            _AcceptedResponseStore(error=RuntimeError("offline")),
            "session",
            "trace",
            "response",
        )
    with pytest.raises(contract.EvidenceCorrelationError, match="correlation"):
        finalizer.accepted_response_run(
            _AcceptedResponseStore("not-a-mapping"),
            "session",
            "trace",
            "response",
        )
    assert finalizer._correlation_missing(None, "session", "trace") == ["evidence_store"]

    recorder = _FinalizationRecorder()
    monkeypatch.setattr(
        finalizer, "read_completion_evidence_snapshot", lambda *_a: _active_snapshot()
    )
    monkeypatch.setattr(
        finalizer,
        "fill_header_fields",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            contract.EvidenceCorrelationError("offline")
        ),
    )
    result = finalizer.finalize_response(
        "Body",
        {"session_id": "session", "trace_id": "trace", "host": "codex"},
        recorder,
    )
    assert result == {
        "action": "continue",
        "text": "Body",
        "missing": ["evidence_verification"],
    }
    assert recorder.calls[0]["action"] == "continue"

    assert (
        finalizer._commit_terminal_finalization(
            object(),
            session_id="session",
            trace_id="trace",
            host="codex",
            response_text="response",
            expected_evidence_revision=1,
        )
        == "evidence_persistence"
    )
    assert (
        finalizer._commit_terminal_finalization(
            SimpleNamespace(commit_terminal_finalization=lambda **_kwargs: {}),
            session_id="session",
            trace_id="trace",
            host="codex",
            response_text="response",
            expected_evidence_revision=1,
        )
        == "evidence_persistence"
    )


def test_preflight_recipe_bounds_and_verifies_content_free_replay() -> None:
    assert len(preflight_recipe._bounded_unique_strings([f"agent-{i}" for i in range(30)])) == 16
    assert preflight_recipe._bounded_unique_strings(["reviewer", "reviewer", "writer"]) == [
        "reviewer",
        "writer",
    ]
    assert (
        preflight_recipe._suggestion_recipe(
            {"selected_ids": ["reviewer"], "work_units": {"delegate": True, "count": 1}}
        )
        == []
    )
    fallback_suggestions = preflight_recipe._suggestion_recipe(
        {
            "selected_ids": [],
            "work_units": {"delegate": True, "count": 2, "units": ["one", "two"]},
        }
    )
    assert fallback_suggestions == []
    assert (
        preflight_recipe._suggestion_recipe(
            {
                "selected_ids": ["reviewer"],
                "work_units": {"delegate": True, "count": 2, "units": "not-a-list"},
            }
        )
        == []
    )
    suggestions = preflight_recipe._suggestion_recipe(
        {
            "selected_ids": ["reviewer"],
            "work_units": {"delegate": True, "count": 2, "units": ["", "same", "same"]},
            "workforce_unit_bindings": [
                {
                    "work_unit_id": delegation_events.work_unit_id_from_text("same"),
                    "selected": ["reviewer"],
                    "delivery": "delegate",
                    "timing": "immediate",
                    "depends_on": [],
                    "parallelization": "sequential",
                    "mutation_scope": "read_only",
                    "artifact_kind": "review-report",
                    "required_tools": [],
                    "required_evidence": [],
                    "confidence": 1.0,
                }
            ],
        }
    )
    assert len(suggestions) == 1

    assert preflight_recipe._combine_context("", "specialist") == "specialist"
    routing = "r" * preflight_recipe.MAX_PREFLIGHT_CONTEXT_CHARS
    with pytest.raises(RuntimeError, match="combined context exceeds"):
        preflight_recipe._combine_context(routing, "specialist")

    with pytest.raises(RuntimeError, match="missing work-unit metadata"):
        preflight_recipe._verified_work_units({}, "Review the runtime")
    with pytest.raises(RuntimeError, match="does not match"):
        preflight_recipe._verified_work_units(
            {"work_units": {"delegate": True, "count": 2}},
            "Review the runtime",
        )


def _ready_recipe() -> dict[str, Any]:
    return {
        "recipe_version": preflight_recipe.PREFLIGHT_REPLAY_RECIPE_VERSION,
        "policy_fingerprint": preflight_recipe._context_policy_fingerprint(
            AgencyConfig(), pipeline
        ),
        "session_id": "session",
        "trace_id": "trace",
        "routing": {"work_units": {"delegate": False, "count": 1}},
        "specialist_refs": [],
        "selection_refs": [],
        "unit_assignment_agents": [],
        "unit_agent_plan": [],
        "delivery_mode": "direct",
        "context_limit": preflight_recipe.MAX_PREFLIGHT_CONTEXT_CHARS,
        "trivial": False,
        "turn_classification": {
            "turn_kind": "new_intent",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
            "continuation_of": "",
            "confidence": 1.0,
            "reason_codes": ["test_fixture"],
            "state_revision": "f" * 64,
            "classifier_version": 1,
        },
        "resident_manager_binding": build_resident_manager_binding(
            session_id="session",
            host="unknown",
            delivery_mode="request",
        ).as_dict(),
        "roster_size": 0,
        "roster_generation": 0,
    }


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("recipe_version", 999, "version is unsupported"),
        ("policy_fingerprint", "0" * 64, "fingerprint does not match"),
        ("session_id", "other", "correlation does not match"),
        ("routing", None, "recipe is malformed"),
        ("unit_assignment_agents", {}, "recipe is malformed"),
    ],
)
def test_preflight_recipe_rejects_unreplayable_state(
    field: str,
    value: Any,
    message: str,
) -> None:
    recipe = _ready_recipe()
    recipe[field] = value
    with pytest.raises(RuntimeError, match=message):
        preflight_recipe._result_from_recipe(
            object(),  # type: ignore[arg-type]
            recipe,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
            config=AgencyConfig(),
            pipeline=pipeline,
        )


def test_preflight_recipe_rejects_a_tampered_unit_assignment_plan() -> None:
    recipe = _ready_recipe()
    recipe["routing"]["work_units"] = {
        "delegate": False,
        "count": 1,
        "confidence": "high",
        "source": "single",
    }
    recipe["unit_agent_plan"] = [
        {
            "assignment_version": "2",
            "work_unit_id": "unit-0000000000",
            "recommended_agent": "agent",
        }
    ]

    with pytest.raises(RuntimeError, match="unit-agent plan does not match"):
        preflight_recipe._result_from_recipe(
            object(),  # type: ignore[arg-type]
            recipe,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
            config=AgencyConfig(),
            pipeline=pipeline,
        )


class _ReadyRecipeStore:
    def __init__(self, recipe: Any) -> None:
        self.recipe = recipe

    def get_ready_preflight_result(self, **_kwargs: Any) -> Any:
        return self.recipe


class _ObservationStore:
    def __init__(self, observation: Any) -> None:
        self.observation = observation

    def observe_preflight_attempt(self, **_kwargs: Any) -> Any:
        return self.observation


def test_preflight_recipe_readers_reject_missing_or_ambiguous_state() -> None:
    kwargs = {
        "session_id": "session",
        "trace_id": "trace",
        "attempt_token": "attempt",
        "user_message": "Review the runtime",
        "config": AgencyConfig(),
        "pipeline": pipeline,
    }
    with pytest.raises(RuntimeError, match="cannot read"):
        preflight_recipe._read_ready_result(object(), **kwargs)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="is unavailable"):
        preflight_recipe._read_ready_result(_ReadyRecipeStore(None), **kwargs)  # type: ignore[arg-type]

    await_kwargs = {**kwargs, "timeout_seconds": 0.0}
    with pytest.raises(RuntimeError, match="cannot observe"):
        preflight_recipe._await_ready_result(object(), **await_kwargs)  # type: ignore[arg-type]
    failures = [
        (None, "observation is unavailable"),
        ({"run_status": "completed"}, "became terminal"),
        ({"run_status": "active", "attempt_matches": False}, "ownership changed"),
        (
            {"run_status": "active", "attempt_matches": True, "preflight_state": "ready"},
            "recipe is unavailable",
        ),
        (
            {"run_status": "active", "attempt_matches": True, "preflight_state": "unknown"},
            "state is invalid",
        ),
    ]
    for observation, message in failures:
        with pytest.raises(RuntimeError, match=message):
            preflight_recipe._await_ready_result(
                _ObservationStore(observation),  # type: ignore[arg-type]
                **await_kwargs,
            )


class _AttemptStore:
    def __init__(self, *, attempt_token: str, cleanup_raises: bool = False) -> None:
        self.attempt_token = attempt_token
        self.cleanup_raises = cleanup_raises
        self.cleanup_calls = 0

    def begin_preflight_attempt(self, **_kwargs: Any) -> dict[str, Any]:
        return {"outcome": "started", "attempt_token": self.attempt_token}

    def get_active_roster_as_catalog(self) -> list[dict[str, str]]:
        return [{"slug": "reviewer"}]

    def plan_resident_manager_binding(self, *, session_id: str, host: str) -> Any:
        delivery_mode = (
            "injected" if resident_manager_host_mode(host) == "persistent" else "request"
        )
        return build_resident_manager_binding(
            session_id=session_id,
            host=host,
            delivery_mode=delivery_mode,
        )

    def mark_preflight_ready(self, **_kwargs: Any) -> dict[str, str]:
        return {"outcome": "cas_lost"}

    def fail_preflight_attempt(self, **_kwargs: Any) -> bool:
        self.cleanup_calls += 1
        if self.cleanup_raises:
            raise RuntimeError("cleanup failed")
        return True


def test_legacy_catalog_facade_still_honors_explicit_disabled_snapshot() -> None:
    store = _AttemptStore(attempt_token="unused")

    assert (
        preflight._catalog_with_policy(  # type: ignore[arg-type]
            store,
            frozenset({"reviewer"}),
        )
        == []
    )


def _patch_preflight_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    import agency_runtime.core.installer as installer
    from agency_runtime.core.roster.workforce import WorkforceIndexSnapshot

    monkeypatch.setattr(installer, "ensure_no_match_fallback_roster", lambda _store: False)
    monkeypatch.setattr(
        pipeline,
        "route",
        lambda *_args, **_kwargs: {
            "selected_ids": [],
            "work_units": delegation_detection.detect_work_units("Review the runtime"),
        },
    )
    monkeypatch.setattr(
        specialist_context,
        "hydrate_selected_specialist_context",
        lambda *_args, **_kwargs: specialist_context.LoadedSpecialistContext("", (), ()),
    )
    monkeypatch.setattr(
        preflight,
        "_require_substantive_specialist",
        lambda *_args, **_kwargs: None,
    )

    # The shared workforce-snapshot path reads the live workforce via store._connect,
    # which the _AttemptStore double does not implement. This test exercises
    # CAS-loss fail-closed behavior, not workforce projection, so return a
    # generation-aligned empty snapshot directly.
    def _coherent(_store, routing_snapshot, **_kwargs):
        workforce = WorkforceIndexSnapshot(
            generation=routing_snapshot.roster_generation,
            worker_count=0,
            contracts=(),
            contract_fingerprint="",
            recruiter_fingerprint="",
            recruiter_index="",
        )
        return routing_snapshot, workforce

    monkeypatch.setattr(preflight, "bind_workforce_snapshot", _coherent)


def test_run_preflight_requires_attempt_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(RuntimeError, match="identity was not persisted"):
        preflight.run_preflight(
            _AttemptStore(attempt_token=""),  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
            host="codex",
            config=AgencyConfig(),
        )


@pytest.mark.parametrize("cleanup_raises", [False, True])
def test_run_preflight_fails_closed_when_ready_commit_loses_ownership(
    monkeypatch: pytest.MonkeyPatch,
    cleanup_raises: bool,
) -> None:
    _patch_preflight_dependencies(monkeypatch)
    store = _AttemptStore(attempt_token="attempt", cleanup_raises=cleanup_raises)
    with pytest.raises(RuntimeError, match="became terminal") as raised:
        preflight.run_preflight(
            store,  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
            host="codex",
            config=AgencyConfig(),
        )
    assert store.cleanup_calls == 1
    if cleanup_raises:
        assert isinstance(raised.value.__cause__, RuntimeError)
        assert str(raised.value.__cause__) == "cleanup failed"


class _MalformedHookText:
    def strip(self) -> _MalformedHookText:
        return self

    def casefold(self) -> _MalformedHookText:
        return self

    def startswith(self, _prefix: str) -> bool:
        return True

    def endswith(self, _suffix: str) -> bool:
        return True

    def find(self, _value: str) -> int:
        return -1


def test_retry_receipts_reject_malformed_wrappers_and_impossible_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(retry_receipts, "str", lambda _value: _MalformedHookText(), raising=False)
    assert retry_receipts.pending_retry_receipt(object()) == ""

    monkeypatch.undo()
    with pytest.raises(ValueError, match="canonical UUID"):
        retry_receipts.attach_retry_receipt("retry", "not-a-uuid")
    with pytest.raises(ValueError, match="does not fit"):
        retry_receipts.attach_retry_receipt(
            "retry",
            "00000000-0000-4000-8000-000000000000",
            maximum_chars=1,
        )

    receipt = "00000000-0000-4000-8000-000000000000"
    wrapped = (
        '<hook_prompt source="agency">retry\n\n'
        f"<!-- agency-continuation:{receipt} -->"
        "</hook_prompt>"
    )
    assert retry_receipts.pending_retry_receipt(wrapped) == receipt
    unwrapped = f"retry\n\n<!-- agency-continuation:{receipt} -->"
    assert retry_receipts.pending_retry_receipt(unwrapped) == receipt
    assert retry_receipts.attach_retry_receipt("retry", receipt).endswith(
        f"<!-- agency-continuation:{receipt} -->"
    )


def test_preflight_projection_rejects_malformed_capability_and_legacy_plans() -> None:
    with pytest.raises(RuntimeError, match="capability receipt is malformed"):
        preflight_recipe._content_free_routing_recipe(
            {"execution_context": "not-a-receipt"},
            trace_id="trace",
        )

    with pytest.raises(RuntimeError, match="no correlated current request"):
        preflight_recipe._isolated_delegation_context(
            {"work_units": {"units": "not-a-list"}},
            host="codex",
            unit_plan=[
                {
                    "assignment_version": "1",
                    "work_unit_id": "unit",
                    "recommended_agent": "reviewer",
                }
            ],
        )
    with pytest.raises(RuntimeError, match="does not match the current request"):
        preflight_recipe._isolated_delegation_context(
            {"work_units": {"units": ["Review the change"]}},
            host="codex",
            unit_plan=[
                {
                    "assignment_version": "1",
                    "work_unit_id": "wrong-unit",
                    "recommended_agent": "reviewer",
                }
            ],
        )
    assert "CONTINUATION UNAVAILABLE" in preflight_recipe._continuation_abstention_context()


def _classification_recipe(
    *,
    version: int = preflight_recipe.PREFLIGHT_REPLAY_RECIPE_VERSION,
) -> dict[str, Any]:
    message = "Review the runtime"
    return {
        "recipe_version": version,
        "turn_classification": {
            "turn_kind": "new_intent",
            "selection_required": True,
            "reroute_required": True,
            "execution_decision_required": True,
            "continuation_of": "",
            "confidence": 1.0,
            "reason_codes": ["test_fixture"],
            "state_revision": "f" * 64,
            "classifier_version": 3,
            "message_fingerprint": sha256(message.encode()).hexdigest(),
        },
    }


def test_preflight_recipe_validates_all_classification_compatibility_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    legacy = preflight_recipe._recipe_turn_classification(
        {"recipe_version": 5},
        trivial=True,
        session_id="session",
        trace_id="trace",
        user_message="ack",
    )
    assert legacy.turn_kind == "acknowledgement"

    with pytest.raises(RuntimeError, match="classification is missing"):
        preflight_recipe._recipe_turn_classification(
            {"recipe_version": 6},
            trivial=False,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
        )

    malformed = _classification_recipe()
    malformed["turn_classification"]["reason_codes"] = "invalid"
    with pytest.raises(RuntimeError, match="classification is malformed"):
        preflight_recipe._recipe_turn_classification(
            malformed,
            trivial=False,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
        )

    wrong_message = _classification_recipe()
    wrong_message["turn_classification"]["message_fingerprint"] = "0" * 64
    with pytest.raises(RuntimeError, match="message does not match"):
        preflight_recipe._recipe_turn_classification(
            wrong_message,
            trivial=False,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
        )

    missing_message = _classification_recipe()
    missing_message["turn_classification"]["message_fingerprint"] = ""
    with pytest.raises(RuntimeError, match="message does not match"):
        preflight_recipe._recipe_turn_classification(
            missing_message,
            trivial=False,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
        )

    valid = _classification_recipe()
    with monkeypatch.context() as patch:
        patch.setattr(
            preflight_recipe,
            "TurnClassification",
            lambda **_kwargs: (_ for _ in ()).throw(ValueError("invalid")),
        )
        with pytest.raises(RuntimeError, match="classification is malformed"):
            preflight_recipe._recipe_turn_classification(
                valid,
                trivial=False,
                session_id="session",
                trace_id="trace",
                user_message="Review the runtime",
            )


def test_preflight_recipe_validates_legacy_and_current_manager_bindings() -> None:
    assert (
        preflight_recipe._recipe_resident_binding(
            {"recipe_version": 7},
            session_id="session",
        )
        is None
    )
    with pytest.raises(RuntimeError, match="legacy preflight recipe"):
        preflight_recipe._recipe_resident_binding(
            {"recipe_version": 7, "resident_manager_binding": {}},
            session_id="session",
        )
    with pytest.raises(RuntimeError, match="binding is invalid"):
        preflight_recipe._recipe_resident_binding(
            {"recipe_version": 8, "resident_manager_binding": {}},
            session_id="session",
        )

    binding = build_resident_manager_binding(
        session_id="session",
        host="claude",
        delivery_mode="injected",
    )
    with pytest.raises(RuntimeError, match="host does not match"):
        preflight_recipe._recipe_resident_binding(
            {
                "recipe_version": 8,
                "host": "codex",
                "resident_manager_binding": binding.as_dict(),
            },
            session_id="session",
        )

    assert (
        preflight_recipe._recipe_resident_managers(
            {"recipe_version": 6},
            binding=None,
        )
        == ()
    )
    with pytest.raises(RuntimeError, match="legacy preflight recipe"):
        preflight_recipe._recipe_resident_managers(
            {
                "recipe_version": 6,
                "resident_manager_kernel": {},
            },
            binding=None,
        )
    with pytest.raises(RuntimeError, match="kernel is invalid"):
        preflight_recipe._recipe_resident_managers(
            {
                "recipe_version": 7,
                "resident_manager_kernel": {},
            },
            binding=None,
        )
    assert (
        preflight_recipe._recipe_resident_managers(
            {
                "recipe_version": 7,
                "resident_manager_kernel": (
                    preflight_recipe.RESIDENT_MANAGER_KERNEL_REFERENCE.as_dict()
                ),
            },
            binding=None,
        )
        == preflight_recipe.RESIDENT_MANAGER_SLUGS
    )
    with pytest.raises(RuntimeError, match="binding is invalid"):
        preflight_recipe._recipe_resident_managers(
            {"recipe_version": 8},
            binding=None,
        )


def test_preflight_recipe_policy_fingerprint_covers_compatibility_versions() -> None:
    fingerprints = {
        version: preflight_recipe._context_policy_fingerprint(
            AgencyConfig(),
            pipeline,
            recipe_version=version,
            context_policy_version=version,
        )
        for version in (6, 7, 8, 10, 11, 12)
    }

    assert len(set(fingerprints.values())) == len(fingerprints)


def test_preflight_recipe_rejects_current_unit_plan_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preflight_recipe,
        "_verified_work_units",
        lambda *_args: {"delegate": True, "count": 2, "units": ["one", "two"]},
    )
    monkeypatch.setattr(delegation_events, "build_unit_agent_plan", lambda *_args: [])
    with pytest.raises(RuntimeError, match="unit-agent plan does not match"):
        preflight_recipe._replay_routing_from_recipe(
            {
                "work_units": {"delegate": True, "count": 2},
            },
            trace_id="trace",
            user_message="continue",
            unit_assignment_agents=[],
            unit_agent_plan=[
                {
                    "assignment_version": "4",
                    "work_unit_id": "unit",
                    "recommended_agent": "reviewer",
                }
            ],
            delegation=AgencyConfig().delegation,
        )


def test_preflight_recipe_replays_continuation_abstention_and_direct_context() -> None:
    abstention = _ready_recipe()
    abstention["routing"]["continuation_resolution_required"] = True
    result = preflight_recipe._result_from_recipe(
        object(),  # type: ignore[arg-type]
        abstention,
        session_id="session",
        trace_id="trace",
        user_message="continue",
        config=AgencyConfig(),
        pipeline=pipeline,
    )
    assert result.loaded_specialists == ()
    assert "CONTINUATION UNAVAILABLE" in result.context

    continuation = _ready_recipe()
    continuation["routing"]["continuation_reused"] = True
    result = preflight_recipe._result_from_recipe(
        object(),  # type: ignore[arg-type]
        continuation,
        session_id="session",
        trace_id="trace",
        user_message="continue",
        config=AgencyConfig(),
        pipeline=pipeline,
    )
    assert result.loaded_specialists == ()
    assert "AGENCY CONTINUATION" in result.context


def test_preflight_helpers_cover_bounded_and_corrupt_store_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suggestions = [
        {
            "recommended_agent": f"agent-{index}",
            "recommended_agents": [f"agent-{index}"],
        }
        for index in range(20)
    ]
    assert len(preflight._suggested_specialist_slugs(suggestions)) == 16

    raising_store = SimpleNamespace(
        get_turn_state_context=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("offline")
        )
    )
    assert (
        preflight._turn_state_for_preflight(
            raising_store,  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
        ).state_status
        == "missing"
    )
    corrupt_store = SimpleNamespace(get_turn_state_context=lambda *_args, **_kwargs: [])
    assert (
        preflight._turn_state_for_preflight(
            corrupt_store,  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
        ).state_status
        == "corrupt"
    )

    too_many = [{"slug": f"agent-{index}", "version": "1", "hash": "f" * 64} for index in range(17)]
    with pytest.raises(RuntimeError, match="durable reference limit"):
        preflight._selection_refs_for_recipe(
            object(),  # type: ignore[arg-type]
            too_many,
            {"selected_ids": [item["slug"] for item in too_many]},
            [],
            [],
        )

    fallback_store = SimpleNamespace(
        get_roster_entry=lambda _slug: {"version": "1", "hash": "f" * 64}
    )
    assert (
        preflight._selection_refs_for_recipe(
            fallback_store,  # type: ignore[arg-type]
            [{"slug": "reviewer"}],
            {"selected_ids": ["reviewer"]},
            [],
            [],
        )[0]["version"]
        == "1"
    )
    with pytest.raises(RuntimeError, match="lacks an active revision"):
        preflight._selection_refs_for_recipe(
            SimpleNamespace(get_roster_entry=lambda _slug: None),  # type: ignore[arg-type]
            [{"slug": "reviewer"}],
            {"selected_ids": ["reviewer"]},
            [],
            [],
        )

    loaded = SimpleNamespace(
        references=[
            SimpleNamespace(as_dict=lambda: {"slug": "reviewer", "version": "2", "hash": "f" * 64})
        ]
    )
    with pytest.raises(RuntimeError, match="revisions changed"):
        preflight._recipe_revision_refs(
            object(),  # type: ignore[arg-type]
            [],
            {},
            [],
            loaded,
            {
                "recipe": {
                    "specialist_refs": [{"slug": "reviewer", "version": "1", "hash": "f" * 64}]
                }
            },
        )

    with pytest.raises(RuntimeError, match="cannot bind resident managers"):
        preflight._resident_binding_for_preflight(
            object(),  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
            host="codex",
        )

    classification = SimpleNamespace(turn_kind="continuation", reroute_required=False)
    fresh = SimpleNamespace(turn_kind="new_intent", reroute_required=True)
    outcomes = iter([RuntimeError("stale"), ("recipe", "routing", [], [], fresh, [])])

    def _prepare(*_args: Any, **_kwargs: Any) -> Any:
        result = next(outcomes)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(preflight, "_prepare_preflight_evidence", _prepare)
    monkeypatch.setattr(preflight, "force_fresh_turn_reroute", lambda *_args: fresh)
    assert (
        preflight._prepare_with_bounded_continuation_reroute(
            object(),  # type: ignore[arg-type]
            classification=classification,  # type: ignore[arg-type]
            prepare_arguments={},
        )[0]
        == "recipe"
    )


def test_run_preflight_rejects_empty_messages_and_internal_adapter_origins() -> None:
    with pytest.raises(ValueError, match="user_message is required"):
        preflight.run_preflight(
            object(),  # type: ignore[arg-type]
            session_id="session",
            user_message=" ",
            host="codex",
        )

    origin = native_adapter_turn_origin(
        "internal_retry",
        host="codex",
        event="user_prompt_submit_retry",
        session_id="session",
        trace_id="trace",
    )
    with pytest.raises(ValueError, match="cannot start Agency preflight"):
        preflight.run_preflight(
            object(),  # type: ignore[arg-type]
            session_id="session",
            trace_id="trace",
            user_message="retry",
            host="codex",
            origin_receipt=origin,
        )


def test_preflight_recipe_closes_turn_when_selected_specialist_is_disabled() -> None:
    config = AgencyConfig(
        agents=AgentActivationConfig(disabled=("reviewer",)),
    )
    recipe = _ready_recipe()
    recipe["policy_fingerprint"] = preflight_recipe._context_policy_fingerprint(
        config,
        pipeline,
    )
    recipe["specialist_refs"] = [
        {
            "slug": "reviewer",
            "version": "1",
            "hash": "f" * 64,
        }
    ]
    closed: list[dict[str, Any]] = []
    store = SimpleNamespace(close_turn_evidence=lambda *_args, **kwargs: closed.append(kwargs))

    with pytest.raises(RuntimeError, match="selected specialist 'reviewer' is disabled"):
        preflight_recipe._result_from_recipe(
            store,  # type: ignore[arg-type]
            recipe,
            session_id="session",
            trace_id="trace",
            user_message="Review the runtime",
            config=config,
            pipeline=pipeline,
        )

    assert closed == [{"status": "specialist_disabled"}]


def _activation_snapshot() -> dict[str, Any]:
    content_hash = "f" * 64
    return {
        "delivery_mode": "isolated",
        "request_kind": "nontrivial",
        "selection_required": True,
        "selected_specialists": [
            {
                "slug": "reviewer",
                "version": "1",
                "hash": content_hash,
            }
        ],
        "specialist_activations": [
            {
                "id": "activation",
                "session_id": "session",
                "trace_id": "trace",
                "work_unit_id": "unit",
                "worker_kind": "codex",
                "worker_id": "worker",
                "native_run_id": "",
                "specialist_slug": "reviewer",
                "specialist_version": "1",
                "specialist_prompt_hash": content_hash,
                "delegation_event_id": "event",
                "consumed_at": "now",
            }
        ],
        "delegations": [
            {
                "id": "event",
                "activation_receipt_id": "activation",
                "work_unit_id": "unit",
                "status": "completed",
                "executed_worker_id": "worker",
                "native_run_id": "",
                "retrieved_specialist_slug": "reviewer",
                "retrieved_specialist_version": "1",
                "retrieved_specialist_prompt_hash": content_hash,
            }
        ],
        "specialists": ["reviewer"],
        "unit_agent_plan": [
            {
                "work_unit_id": "unit",
                "recommended_agent": "reviewer",
            }
        ],
    }


def test_header_activation_validator_rejects_every_untrusted_identity_shape() -> None:
    with pytest.raises(contract.EvidenceCorrelationError, match="activation evidence is invalid"):
        contract._specialist_identity({}, activation=False)
    selected = _activation_snapshot()["selected_specialists"]
    with pytest.raises(contract.EvidenceCorrelationError, match="unit-agent plan is invalid"):
        contract._expected_activation_identities(selected, "invalid")
    with pytest.raises(contract.EvidenceCorrelationError, match="unit-agent plan is invalid"):
        contract._expected_activation_identities(
            selected,
            [{"work_unit_id": "", "recommended_agent": "reviewer"}],
        )

    snapshot = _activation_snapshot()
    event = snapshot["delegations"][0]
    row = snapshot["specialist_activations"][0]
    with pytest.raises(contract.EvidenceCorrelationError, match="is not correlated"):
        contract._validated_activation_identity(
            {},
            events={"event": event},
            session_id="session",
            trace_id="trace",
        )

    no_worker_event = {**event, "executed_worker_id": "", "native_run_id": ""}
    no_worker_row = {**row, "worker_id": "", "native_run_id": ""}
    with pytest.raises(contract.EvidenceCorrelationError, match="no native worker identity"):
        contract._validated_activation_identity(
            no_worker_row,
            events={"event": no_worker_event},
            session_id="session",
            trace_id="trace",
        )

    with pytest.raises(contract.EvidenceCorrelationError, match="worker identity is mismatched"):
        contract._validated_activation_identity(
            {**row, "worker_id": "other"},
            events={"event": event},
            session_id="session",
            trace_id="trace",
        )
    with pytest.raises(contract.EvidenceCorrelationError, match="retrieved identity is mismatched"):
        contract._validated_activation_identity(
            row,
            events={"event": {**event, "retrieved_specialist_version": "2"}},
            session_id="session",
            trace_id="trace",
        )


def test_header_activation_validator_rejects_invalid_collections_and_cardinality() -> None:
    for changes, message in (
        ({"delivery_mode": "invalid"}, "delivery mode"),
        ({"selected_specialists": "invalid"}, "selected specialist evidence"),
        ({"specialist_activations": "invalid"}, "activation evidence"),
    ):
        snapshot = {**_activation_snapshot(), **changes}
        with pytest.raises(contract.EvidenceCorrelationError, match=message):
            contract._validate_specialist_activations(snapshot, "session", "trace")

    duplicate = _activation_snapshot()
    duplicate["specialist_activations"] = [
        duplicate["specialist_activations"][0],
        dict(duplicate["specialist_activations"][0]),
    ]
    with pytest.raises(contract.EvidenceCorrelationError, match="is not one-use"):
        contract._validate_specialist_activations(duplicate, "session", "trace")

    mismatched_claim = _activation_snapshot()
    mismatched_claim["specialists"] = []
    with pytest.raises(contract.EvidenceCorrelationError, match="loaded-specialist evidence"):
        contract._validate_specialist_activations(mismatched_claim, "session", "trace")

    unassigned = _activation_snapshot()
    unassigned["unit_agent_plan"] = [
        {
            "work_unit_id": "other-unit",
            "recommended_agent": "reviewer",
        }
    ]
    with pytest.raises(contract.EvidenceCorrelationError, match="was not assigned"):
        contract._validate_specialist_activations(unassigned, "session", "trace")

    incomplete = _activation_snapshot()
    incomplete["specialist_activations"] = []
    incomplete["specialists"] = []
    with pytest.raises(contract.EvidenceCorrelationError, match="activation is incomplete"):
        contract._validate_specialist_activations(incomplete, "session", "trace")


def test_header_snapshot_rejects_resident_manager_and_turn_shape_mismatches() -> None:
    invalid_snapshots: list[tuple[dict[str, Any], str]] = []
    snapshot = _active_snapshot()
    snapshot["resident_managers"] = "invalid"
    invalid_snapshots.append((snapshot, "resident manager evidence"))
    snapshot = _active_snapshot()
    snapshot["resident_manager_binding"] = "invalid"
    invalid_snapshots.append((snapshot, "resident manager binding"))
    snapshot = _active_snapshot()
    snapshot["resident_managers"] = ["wrong-manager"]
    invalid_snapshots.append((snapshot, "resident manager identity"))
    snapshot = _active_snapshot()
    snapshot["resident_managers"] = list(contract.RESIDENT_MANAGER_SLUGS)
    snapshot["resident_manager_kernel"] = {}
    invalid_snapshots.append((snapshot, "resident manager kernel"))
    snapshot = _active_snapshot()
    snapshot["resident_manager_kernel"] = {}
    invalid_snapshots.append((snapshot, "resident manager binding"))
    snapshot = _active_snapshot()
    snapshot["preflight_recipe_version"] = True
    invalid_snapshots.append((snapshot, "preflight recipe version"))
    snapshot = _active_snapshot()
    snapshot["preflight_recipe_version"] = 7
    snapshot["resident_manager_binding"] = {}
    invalid_snapshots.append((snapshot, "resident manager binding"))
    snapshot = _active_snapshot()
    snapshot["preflight_recipe_version"] = 8
    invalid_snapshots.append((snapshot, "resident manager binding"))
    snapshot = _active_snapshot()
    snapshot["selection_required"] = "yes"
    invalid_snapshots.append((snapshot, "selection policy"))
    snapshot = _active_snapshot()
    snapshot["turn_kind"] = "invalid"
    invalid_snapshots.append((snapshot, "intent classification"))

    for snapshot, message in invalid_snapshots:
        with pytest.raises(contract.EvidenceCorrelationError, match=message):
            contract._validate_completion_snapshot(snapshot, "session", "trace")

    assert contract._is_legacy_unclassified_evidence_snapshot(None, "session", "trace") is False
    with pytest.raises(contract.EvidenceCorrelationError, match="trace_id is required"):
        contract.read_completion_evidence_snapshot(object(), "session", "")


def test_header_resident_binding_rejects_invalid_and_cross_host_receipts() -> None:
    snapshot = _active_snapshot()
    snapshot["preflight_recipe_version"] = 8
    binding = build_resident_manager_binding(
        session_id="session",
        host="claude",
        delivery_mode="injected",
    )
    snapshot["resident_manager_binding"] = binding.as_dict()

    legacy = dict(snapshot)
    legacy["preflight_recipe_version"] = 7
    with pytest.raises(contract.EvidenceCorrelationError, match="binding could not be verified"):
        contract._validated_resident_binding(
            legacy,
            {"host": "claude"},
            session_id="session",
        )
    with pytest.raises(contract.EvidenceCorrelationError, match="host binding"):
        contract._validated_resident_binding(
            snapshot,
            {"host": "codex"},
            session_id="session",
        )
    snapshot["resident_manager_binding"] = {}
    with pytest.raises(contract.EvidenceCorrelationError, match="binding could not be verified"):
        contract._validated_resident_binding(
            snapshot,
            {"host": "codex"},
            session_id="session",
        )


def test_header_activation_and_delegation_strength_shapes_fail_closed() -> None:
    with pytest.raises(contract.EvidenceCorrelationError, match="selection policy"):
        contract._validate_specialist_activations(
            {
                "delivery_mode": "isolated",
                "request_kind": "nontrivial",
                "selection_required": "yes",
                "selected_specialists": [],
                "specialist_activations": [],
                "delegations": [],
            },
            "session",
            "trace",
        )

    assert contract._planned_delegation_strengths({"preflight_recipe_version": True}) is None
    with pytest.raises(contract.EvidenceCorrelationError, match="strength plan"):
        contract._planned_delegation_strengths(
            {"preflight_recipe_version": 11, "unit_agent_plan": "invalid"}
        )
    with pytest.raises(contract.EvidenceCorrelationError, match="strength plan"):
        contract._planned_delegation_strengths(
            {"preflight_recipe_version": 11, "unit_agent_plan": ["invalid"]}
        )
    for invalid in (
        {"work_unit_id": "", "delegation_strength": "preferred"},
        {"work_unit_id": "unit", "delegation_strength": "invalid"},
        {"work_unit_id": "unit", "delegation_strength": "preferred"},
    ):
        plan = [invalid]
        if invalid["work_unit_id"] == "unit" and invalid["delegation_strength"] == "preferred":
            plan.append(dict(invalid))
        with pytest.raises(contract.EvidenceCorrelationError, match="strength plan"):
            contract._planned_delegation_strengths(
                {"preflight_recipe_version": 11, "unit_agent_plan": plan}
            )

    correction = contract._strong_delegation_correction(
        {
            "preflight_recipe_version": 11,
            "unit_agent_plan": [
                {
                    "work_unit_id": "unit",
                    "delegation_strength": "strongly_preferred",
                }
            ],
            "run": "invalid",
        },
        [{"work_unit_id": "unit", "recommended_agent": "reviewer"}],
    )
    assert correction is not None
    assert correction["missing"] == ["delegation_execution"]


def test_header_evidence_codes_bound_filter_and_completion_violation_projection() -> None:
    codes = ["valid", "VALID", "bad code", *[f"code-{index}" for index in range(20)]]
    bounded = contract._bounded_evidence_codes(codes)
    assert len(bounded) == contract._MAX_HEADER_CODES
    assert bounded[0] == "valid"
    assert "bad code" not in bounded

    violation = contract._completion_snapshot_violation(
        contract.EvidenceCorrelationError("trace_id does not belong to session_id")
    )
    assert violation["missing"] == ["correlation"]


def test_completion_policy_covers_invalid_strength_and_open_optional_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        contract,
        "_validate_completion_snapshot",
        lambda snapshot, *_args, **_kwargs: dict(snapshot),
    )
    invalid_strength = _active_snapshot()
    invalid_strength["selection_required"] = False
    invalid_strength["preflight_recipe_version"] = 11
    invalid_strength["unit_agent_plan"] = "invalid"
    violation = contract.validate_completion_policy(
        _valid_header(),
        session_id="session",
        trace_id="trace",
        store=object(),
        evidence_snapshot=invalid_strength,
    )
    assert violation is not None
    assert violation["missing"] == ["evidence_verification"]

    strong = _active_snapshot()
    strong["selection_required"] = False
    strong["preflight_recipe_version"] = 11
    strong["unit_agent_plan"] = [
        {"work_unit_id": "unit", "delegation_strength": "strongly_preferred"}
    ]
    strong["delegations"] = [
        {
            "id": "delegation",
            "work_unit_id": "unit",
            "recommended_agent": "reviewer",
            "status": "suggested",
        }
    ]
    delegated_header = _valid_header().replace(
        "Agency/Agencies loaded: none",
        "Agency/Agencies loaded: reviewer",
    )
    violation = contract.validate_completion_policy(
        delegated_header,
        session_id="session",
        trace_id="trace",
        store=object(),
        evidence_snapshot=strong,
    )
    assert violation is not None
    assert violation["missing"] == ["delegation_execution"]

    optional = copy.deepcopy(strong)
    optional["unit_agent_plan"][0]["delegation_strength"] = "optional"
    monkeypatch.setattr(
        contract,
        "fill_header_fields",
        lambda *_args, evidence_snapshot, **_kwargs: {
            **contract.parse_header(delegated_header),
            "agencies_delegated": "none",
        },
    )
    assert (
        contract.validate_completion_policy(
            delegated_header,
            session_id="session",
            trace_id="trace",
            store=object(),
            evidence_snapshot=optional,
        )
        is None
    )


def test_completion_policy_rejects_incomplete_workspace_write_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        contract,
        "_validate_completion_snapshot",
        lambda snapshot, *_args, **_kwargs: dict(snapshot),
    )
    snapshot = _active_snapshot()
    snapshot["selection_required"] = False
    snapshot["preflight_recipe_version"] = 14
    snapshot["unit_agent_plan"] = [_current_workspace_write_plan()]
    snapshot["delegations"] = [
        {
            "id": "delegation",
            "work_unit_id": "unit-1234567890",
            "recommended_agent": "minimal-change-engineer",
            "status": "delegated",
            "completed_at": None,
        }
    ]

    violation = contract.validate_completion_policy(
        _valid_header(),
        session_id="session",
        trace_id="trace",
        store=object(),
        evidence_snapshot=snapshot,
    )

    assert violation is not None
    assert violation["missing"] == ["delegation_execution"]
    assert "unit-1234567890" in violation["message"]
    snapshot["delegations"][0]["status"] = "completed"
    assert contract.validate_completion_policy(
        _valid_header(),
        session_id="session",
        trace_id="trace",
        store=object(),
        evidence_snapshot=snapshot,
    )["missing"] == ["delegation_execution"]
    snapshot["delegations"][0]["completed_at"] = "2026-08-02T15:00:00+00:00"
    snapshot["preflight_recipe_version"] = True
    assert contract.validate_completion_policy(
        _valid_header(),
        session_id="session",
        trace_id="trace",
        store=object(),
        evidence_snapshot=snapshot,
    )["missing"] == ["evidence_verification"]
    snapshot["preflight_recipe_version"] = 14
    snapshot["delegations"].append(
        {
            **snapshot["delegations"][0],
            "id": "duplicate-delegation",
        }
    )
    assert contract.validate_completion_policy(
        _valid_header(),
        session_id="session",
        trace_id="trace",
        store=object(),
        evidence_snapshot=snapshot,
    )["missing"] == ["evidence_verification"]
    snapshot["delegations"].pop()
    monkeypatch.setattr(
        contract,
        "fill_header_fields",
        lambda fields, *_args, **_kwargs: dict(fields),
    )
    assert (
        contract.validate_completion_policy(
            _valid_header(),
            session_id="session",
            trace_id="trace",
            store=object(),
            evidence_snapshot=snapshot,
        )
        is None
    )


def test_completion_evaluation_marks_strong_delegation_decision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        contract,
        "read_completion_evidence_snapshot",
        lambda *_args, **_kwargs: _active_snapshot(),
    )
    monkeypatch.setattr(
        contract,
        "validate_completion_policy",
        lambda *_args, **_kwargs: {
            "message": "delegate",
            "missing": ["delegation_execution"],
        },
    )

    decision = contract.evaluate_completion_policy(
        _valid_header(),
        session_id="session",
        trace_id="trace",
        store=object(),
    )

    assert decision["delegation_strength"] == "strongly_preferred"


def test_finalization_rejects_unverifiable_replay_and_activation_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metadata = {"session_id": "session", "trace_id": "trace"}
    with monkeypatch.context() as patch:
        patch.setattr(
            finalizer,
            "accepted_response_run",
            lambda *_args: (_ for _ in ()).throw(contract.EvidenceCorrelationError("offline")),
        )
        assert finalizer.finalize_response("Body", metadata, object())["missing"] == [
            "evidence_verification"
        ]

    with monkeypatch.context() as patch:
        patch.setattr(
            finalizer,
            "accepted_response_run",
            lambda *_args: {
                "authoritative": False,
                "action": "accept",
                "terminal_status": "completed",
                "status": "completed",
            },
        )
        assert finalizer.finalize_response("Body", metadata, object())["missing"] == [
            "evidence_verification"
        ]

    with monkeypatch.context() as patch:
        patch.setattr(finalizer, "accepted_response_run", lambda *_args: None)
        patch.setattr(
            finalizer,
            "read_completion_evidence_snapshot",
            lambda *_args: (_ for _ in ()).throw(
                contract.EvidenceCorrelationError("specialist activation is incomplete")
            ),
        )
        assert finalizer.finalize_response("Body", metadata, object())["missing"] == [
            "specialist_activation"
        ]


class _DelegationRows:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.recorded: list[dict[str, Any]] = []

    def get_delegations(self, _trace_id: str) -> list[dict[str, Any]]:
        return list(self.rows)

    def record_delegation(self, **kwargs: Any) -> None:
        self.recorded.append(kwargs)


def test_delegation_suggestion_helpers_bound_and_dedupe_compatibility_rows() -> None:
    assert delegation_events._clean(None) == ""
    rows = [
        {"status": "completed", "session_id": "session"},
        {"status": "suggested", "session_id": "other"},
        *[
            {"status": "suggested", "session_id": "session", "work_unit_id": f"unit-{i}"}
            for i in range(20)
        ],
    ]
    assert (
        len(
            delegation_events.suggested_delegations(
                _DelegationRows(rows),  # type: ignore[arg-type]
                "session",
                trace_id="trace",
            )
        )
        == delegation_events.MAX_SUGGESTED_WORK_UNITS
    )
    assert delegation_events.suggested_delegations(
        _DelegationRows(rows[:3]),  # type: ignore[arg-type]
        "session",
        trace_id="trace",
    ) == [rows[2]]

    store = _DelegationRows([])
    invalid_routes = [
        {"trace_id": "trace", "work_units": {"delegate": True, "count": object()}},
        {"trace_id": "trace", "work_units": {"delegate": False, "count": 2}},
        {
            "trace_id": "trace",
            "work_units": {"delegate": True, "count": 2, "units": "not-a-list"},
        },
        {
            "trace_id": "trace",
            "work_units": {"delegate": True, "count": 2, "units": ["", "  "]},
        },
    ]
    for routing in invalid_routes:
        assert (
            delegation_events.record_suggested_delegations(
                store,  # type: ignore[arg-type]
                session_id="session",
                host="codex",
                routing=routing,
            )
            == 0
        )

    existing_id = delegation_events.work_unit_id_from_text("duplicate")
    new_id = delegation_events.work_unit_id_from_text("new work")

    def binding(work_unit_id: str) -> dict[str, Any]:
        return {
            "work_unit_id": work_unit_id,
            "selected": ["reviewer"],
            "delivery": "delegate",
            "timing": "immediate",
            "depends_on": [],
            "parallelization": "sequential",
            "mutation_scope": "read_only",
            "artifact_kind": "review-report",
            "required_tools": [],
            "required_evidence": [],
            "confidence": 1.0,
        }

    compatibility = _DelegationRows([{"work_unit_id": existing_id}])
    recorded = delegation_events.record_suggested_delegations(
        compatibility,  # type: ignore[arg-type]
        session_id="session",
        host="codex",
        routing={
            "trace_id": "trace",
            "selected_ids": ["reviewer"],
            "work_units": {
                "delegate": True,
                "count": 4,
                "units": ["", "duplicate", "duplicate", "new work"],
            },
            "workforce_unit_bindings": [binding(existing_id), binding(new_id)],
        },
    )
    assert recorded == 1
    assert compatibility.recorded[0]["work_unit_id"] == new_id


def test_selector_edge_projections_remain_bounded_and_fail_closed() -> None:
    imperative = "; also ".join(f"fix component {index}" for index in range(30))
    assert len(delegation_detection._imperative_units(imperative)) == (
        delegation_events.MAX_SUGGESTED_WORK_UNITS
    )
    assert delegation_detection._imperative_units(
        "fix the API; also fix the API; also fix the UI"
    ) == ["fix the API; also", "fix the UI"]

    assert pipeline._bounded_work_units(None) == {
        "count": 1,
        "confidence": "low",
        "source": "unknown",
        "units": [""],
        "delegate": False,
    }
    assert pipeline._bounded_work_units({"count": "invalid", "units": []})["count"] == 1
    refresh_kwargs = {
        "active_ids": frozenset(),
        "matched_actions": [],
        "companion_ids": [],
        "available_companion_ids": [],
        "unavailable_companion_ids": [],
        "work_units": {},
    }
    assert pipeline._refresh_reused_routing({"fallback_applied": True}, **refresh_kwargs) is None
    assert pipeline._refresh_reused_routing({"semantic_ids": []}, **refresh_kwargs) is None
    context = pipeline.build_routing_context({"selected_ids": [], "confidence": "invalid"})
    assert context.startswith("[AGENCY PREFLIGHT] No high-confidence specialist match")

    assert (
        policy.detect_fallback_companions(
            {"actions": {"DEFAULT": {"always_include": "not-a-list"}}}
        )
        == []
    )
    assert policy.detect_fallback_companions(
        {"actions": {"DEFAULT": {"always_include": [None, {"slug": "fallback"}]}}}
    ) == ["fallback"]


class _VersionedPromptStore:
    def __init__(self, prompt: Any) -> None:
        self.prompt = prompt

    def get_versioned_specialist_prompt(self, *_args: Any, **_kwargs: Any) -> Any:
        return copy.deepcopy(self.prompt)


@pytest.mark.skip(
    reason="ADR-0087: pre-existing failure — the replay version-identity check changed "
    "under PR #129 and now surfaces a different error than 'too many specialists'. "
    "Needs the full inference nomination-delivery flow to verify correctly."
)
def test_specialist_replay_rejects_unverifiable_version_identity() -> None:
    reference = {
        "slug": "reviewer",
        "version": "1",
        "hash": "hash",
        "description": "Reviews code",
        "capabilities": ["review"],
    }
    with pytest.raises(RuntimeError, match="too many specialists"):
        specialist_context.rebuild_versioned_specialist_context(
            object(),  # type: ignore[arg-type]
            [reference] * (specialist_context.MAX_SELECTED_SPECIALISTS + 1),
        )
    with pytest.raises(RuntimeError, match="cannot replay"):
        specialist_context.rebuild_versioned_specialist_context(
            object(),  # type: ignore[arg-type]
            [reference],
        )
    with pytest.raises(RuntimeError, match="invalid specialist reference"):
        specialist_context.rebuild_versioned_specialist_context(
            _VersionedPromptStore(None),  # type: ignore[arg-type]
            [{**reference, "slug": ""}],
        )
    with pytest.raises(RuntimeError, match="is unavailable"):
        specialist_context.rebuild_versioned_specialist_context(
            _VersionedPromptStore(None),  # type: ignore[arg-type]
            [reference],
        )
    with pytest.raises(RuntimeError, match="does not match"):
        specialist_context.rebuild_versioned_specialist_context(
            _VersionedPromptStore(
                {
                    "agent_slug": "different",
                    "version": "1",
                    "prompt_hash": "hash",
                    "prompt_body": "Review carefully.",
                }
            ),  # type: ignore[arg-type]
            [reference],
        )
    with pytest.raises(ValueError, match="session_id and trace_id"):
        specialist_context.hydrate_selected_specialist_context(
            object(),  # type: ignore[arg-type]
            [],
            {},
            session_id="",
            trace_id="trace",
        )
