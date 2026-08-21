"""Rule 6 on every host: no card found, so one is made, interviewed, and filed.

The contractor path itself already had thorough host-neutral coverage. What it
did not have was any evidence that the ladder actually runs inside a real turn
on a real host boundary -- which is what Rule 9 asks of every rule.

Each case drives the host's own entry point for an ordinary user turn with a
request the roster cannot cover, and follows the whole ladder: inference proves
the gap, an independent critic and a security review pass on it, the contractor
is filed in the pool under `origin='agency'`, and it is dealt into that same
turn. A second turn then finds it already in the pool -- "file it for next
time" is the half of the rule a single-turn assertion would miss.

Only inference is stubbed (ADR-0118). Everything else is the production path,
including the deterministic duplicate, safety, and enablement checks that can
still refuse a hire the model asked for.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.hooks import HookBridge
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.structured_provider import StructuredProviderResult

_MESSAGE = "Implement the missing quantum compiler build integration."
_UNIT_ID = "unit-quantum-build"
_CONTRACTOR = "quantum-build-engineer"
_NEAREST = "code-reviewer"

_HOSTS = ("claude", "codex", "zcode", "hermes", "openclaw")

# `workforce.provider` is not optional here: hiring declines silently without
# one, and the decline reads as an ordinary abstention rather than a
# misconfiguration.
_CONFIG = """judge:
  model: ""
ollama:
  enabled: false
providers:
  - name: task-agency-router
    type: litellm
    model: router-alias
    base_url: https://router.example.test/v1
    api_key: secret
workforce:
  provider: task-agency-router
store:
  db_path: {db_path}
"""


def _result(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="gpt-5.6-mini",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def _employment_contract() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "slug": _CONTRACTOR,
        "role": "Quantum Build Engineer",
        "narrow_scope": "Portable TypeScript build plugins for quantum compiler toolchains.",
        "outcomes_owned": ["quantum-build-implementation"],
        "artifacts_produced": ["implementation-change"],
        "capabilities": ["quantum-build-systems", "implementation"],
        "anti_capabilities": ["General product architecture is outside this role."],
        "preferred_scenarios": ["A quantum compiler needs portable TypeScript build integration."],
        "avoided_scenarios": ["Generic frontend feature implementation."],
        "forbidden_scenarios": ["Production deployment approval."],
        "lifecycle_phases": ["implementation"],
        "authority": "modify",
        # Rule 2 inverted if this were `isolated_only`: the card could never
        # load into the caller that needed it.
        "context_mode": "direct_safe",
        "external_mutation": False,
        "tools": ["repository-read"],
        "platforms": ["windows", "linux"],
        "hosts": list(_HOSTS),
        "requirements": ["Operate only on the assigned build plugin."],
        "relationships": [],
        "evidence_requirements": ["Windows and Linux build evidence."],
        "closest_workers": [
            {
                "worker": _NEAREST,
                "insufficiency": "Reviews code but cannot implement the quantum build plugin.",
                "differentiation": "Owns narrow TypeScript quantum compiler build implementation.",
            }
        ],
        "positive_evaluations": [
            {
                "case_id": "positive-quantum-build",
                "scenario": "Implement the cross-platform quantum compiler build plugin.",
                "expectation": "select",
                "rationale": "The requested artifact is the contractor's narrow specialty.",
            }
        ],
        "hard_negative_evaluations": [
            {
                "case_id": "negative-generic-review",
                "scenario": "Review a standard web application build configuration.",
                "expectation": "select_other",
                "rationale": "A general code reviewer is the safer specialist.",
            }
        ],
        "execution_profile": {
            "inspect_before_acting": [
                "Inspect package metadata, compiler interfaces, supported platforms, and repository policy."
            ],
            "working_principles": [
                "Keep build integration deterministic, typed, portable, and bounded to the assigned plugin."
            ],
            "failure_modes_to_check": [
                "Check module drift, invalid compiler input, partial output, and platform path differences."
            ],
            "verification_steps": [
                "Run focused build success and failure tests on the declared Windows and Linux boundaries."
            ],
            "stop_conditions": [
                "Stop when the compiler contract or supported platform behavior cannot be established."
            ],
        },
    }


def _hiring_response() -> dict[str, Any]:
    return {
        "action": "hire",
        "decision_reason": "The complete workforce lacks the narrow implementation capability.",
        "gap_evidence": {
            "gap_proven": True,
            "uncovered_work_unit": _UNIT_ID,
            "missing_capabilities": ["quantum-build-systems"],
            "nearest_workers": [
                {
                    "agent_id": _NEAREST,
                    "insufficiency": "Review authority cannot implement this specialized plugin.",
                    "overlap_score": 0.31,
                }
            ],
            "disabled_covering_workers": [],
            "required_scope": "Narrow portable quantum compiler build plugin implementation.",
            "expected_reuse": "Reusable for future quantum compiler packages.",
        },
        "duplicate_evidence": {
            "decision": "hire",
            "closest_workers": [_NEAREST],
            "maximum_overlap": 0.31,
            "coherent_amendment_target": "",
            "reason": "Authority and domain differ, so amendment would be incoherent.",
        },
        "contract": _employment_contract(),
    }


def _plan_response(*, novel: str) -> dict[str, Any]:
    return {
        "request_summary": "Build the quantum compiler plugin.",
        "units": [
            {
                "unit_id": _UNIT_ID,
                "outcome": "Implement a portable quantum compiler build plugin.",
                "artifact_kind": "implementation-change",
                "domains": ["quantum-build-systems"],
                "stacks": ["typescript"],
                "capability_ids": ["implementation"],
                "novel_capability": novel,
                "depends_on": [],
            }
        ],
    }


def _invoker(stages: list[str], *, recruiter_finds: str = ""):
    """Answer each inference stage, keyed by the schema it is asked for.

    `recruiter_finds` names a worker the recruiter can staff the unit with. Empty
    means it reports a gap, which is what starts the hiring ladder. The plan
    tracks it: once the contractor exists, the capability it was hired for is no
    longer novel, and a plan that still claimed it would be rejected.
    """

    def invoke(_provider: Any, _prompt: Any, schema: Any, **_kwargs: Any):
        keys = set(schema.get("properties", {}) if isinstance(schema, Mapping) else {})
        if "request_summary" in keys and "units" in keys:
            stages.append("planner")
            novel = "" if recruiter_finds else "quantum-build-systems"
            return _result(_plan_response(novel=novel))
        if "action" in keys and "gap_evidence" in keys:
            stages.append("hiring")
            return _result(_hiring_response())
        if "verdict" in keys:
            stages.append("security_review")
            return _result(
                {
                    "verdict": "safe",
                    "reasons": [],
                    "required_changes": [],
                    "same_provider_as_creator_warning": False,
                }
            )
        if "approved" in keys:
            # Both the hiring critic and the staffing assurance critic answer this
            # schema, so the label stays generic and the assertions below key on
            # the stages only hiring can produce.
            stages.append("critic")
            return _result({"approved": True, "reason_codes": []})
        if "units" in keys:
            stages.append("recruiter")
            ranked = (
                [
                    {
                        "agent_id": recruiter_finds,
                        "score": 0.99,
                        "classification": "required",
                        "positive_evidence": ["scope-match"],
                        "negative_evidence": [],
                    }
                ]
                if recruiter_finds
                else []
            )
            return _result(
                {
                    "units": [
                        {
                            "unit_id": _UNIT_ID,
                            "decision": "staff" if recruiter_finds else "gap",
                            "ranked_semantic": ranked,
                        }
                    ]
                }
            )
        raise AssertionError(f"unstubbed inference stage: {sorted(keys)}")

    return invoke


def _bind_inference(monkeypatch: pytest.MonkeyPatch, invoke: Any) -> None:
    """Point every inference seam at one stub, including hiring's own default.

    `hire_contractor_for_gap` binds the real invoker as a default argument at
    import time, so patching the inference module alone leaves hiring calling a
    live provider -- which fails as a silent abstention rather than an error.
    """

    from agency_runtime.core.workforce import hiring as hiring_module
    from agency_runtime.core.workforce import inference as inference_module

    monkeypatch.setattr(inference_module, "invoke_structured_provider_result", invoke)
    original_hire = hiring_module.hire_contractor_for_gap

    def _hire(*args: Any, **kwargs: Any):
        kwargs["invoker"] = invoke
        return original_hire(*args, **kwargs)

    monkeypatch.setattr(hiring_module, "hire_contractor_for_gap", _hire)


def _configured_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    from tests.runtime_support import harden_private_test_file

    db_path = tmp_path / "agency.db"
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(_CONFIG.format(db_path=db_path), encoding="utf-8")
    harden_private_test_file(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    return Store(db_path)


def _take_a_turn(host: str, store: Store, *, session_id: str, trace_id: str) -> str:
    """Run one ordinary user turn through the host's own entry point."""

    if host in {"claude", "codex", "zcode"}:
        result = HookBridge(host, store=store).handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "turn_id": trace_id,
                "prompt": _MESSAGE,
            }
        )
        output = result.get("hookSpecificOutput") or {}
        return str(output.get("additionalContext") or "")

    adapter_type: Any = HermesAdapter if host == "hermes" else OpenClawAdapter
    projection = adapter_type(store=store).pre_llm_call_handler(
        session_id,
        _MESSAGE,
        trace_id=trace_id,
    )
    return str((projection or {}).get("context") or "")


@pytest.mark.parametrize("host", _HOSTS)
def test_an_uncovered_turn_mints_interviews_and_files_a_contractor(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 6 on every host, inside one real turn."""

    store = _configured_store(tmp_path, monkeypatch)
    stages: list[str] = []
    _bind_inference(monkeypatch, _invoker(stages))
    session_id = f"{host}-r6-session"
    trace_id = f"{host}-r6-turn"

    context = _take_a_turn(host, store, session_id=session_id, trace_id=trace_id)

    # The card did not exist, so it was made -- and interviewed before use. An
    # approving critic and a security review are both required stages, not
    # decoration: a hire nobody vetted is the failure this rule guards against.
    assert stages == ["planner", "recruiter", "hiring", "critic", "security_review"]

    entry = store.get_roster_entry(_CONTRACTOR)
    assert entry is not None, "the contractor was never filed in the pool"
    assert entry["audit_status"] == "approved"
    assert entry["routing_contract_valid"] is True
    assert host in entry["supported_hosts"]

    # Filed in the contractor lane, not quietly as an upstream worker, and
    # carrying a body the next turn can actually deal.
    worker = store.get_workforce_worker(_CONTRACTOR)
    assert worker["origin"] == "agency"
    assert worker["employment_class"] == "contractor"
    assert store.get_specialist_prompt(_CONTRACTOR), "the filed contractor has no usable prompt"

    # And it was dealt into the very turn whose gap created it.
    assert _CONTRACTOR in context, context
    assert store.get_specialists_for_trace(session_id, trace_id) == [_CONTRACTOR]


@pytest.mark.parametrize("host", _HOSTS)
def test_a_filed_contractor_is_reused_next_time_without_hiring_again(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filing it in the pool for next time is half the rule, so prove next time."""

    store = _configured_store(tmp_path, monkeypatch)
    first_stages: list[str] = []
    _bind_inference(monkeypatch, _invoker(first_stages))
    session_id = f"{host}-r6-reuse-session"

    _take_a_turn(host, store, session_id=session_id, trace_id=f"{host}-r6-reuse-one")
    assert "hiring" in first_stages

    second_stages: list[str] = []
    _bind_inference(monkeypatch, _invoker(second_stages, recruiter_finds=_CONTRACTOR))
    context = _take_a_turn(host, store, session_id=session_id, trace_id=f"{host}-r6-reuse-two")

    # The pool answered this time: the turn planned and recruited, and neither
    # hiring nor its security review ran, so no second contractor was minted
    # for a gap that had already been filled.
    assert second_stages[:2] == ["planner", "recruiter"]
    assert "hiring" not in second_stages
    assert "security_review" not in second_stages
    assert _CONTRACTOR in context, context
    assert store.get_specialists_for_trace(session_id, f"{host}-r6-reuse-two") == [_CONTRACTOR]
