from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib

from agency_runtime.core import canary
from agency_runtime.core.canary_proof import (
    _codex_product_collaboration_projection,
    codex_product_activation_failures,
)
from agency_runtime.core.codex_child_tool_evidence import (
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS,
    CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA,
)
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.delegation.native_labels import codex_task_name_for_work_unit
from agency_runtime.core.evals import product_host
from agency_runtime.core.evals.product_host import execute_product_host
from agency_runtime.core.workforce.routing_projection import (
    workforce_work_units_from_descriptors,
)


def _hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _workspace_trust(workdir: str) -> dict[str, object]:
    normalized = str(Path(workdir).resolve())
    if os.name == "nt":
        normalized = normalized.casefold()
    return {
        "schema": "agency.codex-isolated-workspace-trust.v1",
        "status": "trusted",
        "scope": "exact-workspace",
        "workspace_hash": "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "persistent_profile_changed": False,
    }


def test_workspace_write_proof_is_owned_by_a_delegated_workspace_write_unit() -> None:
    wrapped, token = product_host._prompt_with_workspace_write_proof("Build the product.", "a" * 64)

    assert "terminal `mutation_scope` field" in wrapped
    assert "with `mutation_scope=workspace_write`" in wrapped
    assert "If it is absent, create it" in wrapped
    assert "first mutation with `apply_patch`" in wrapped
    assert "Read-only children and the non-working parent must not create it" in wrapped
    assert token in wrapped

    goals = workforce_work_units_from_descriptors(
        wrapped,
        (
            {
                "ordinal": 1,
                "artifact_kind": "analysis",
                "lifecycle_phase": "discovery",
                "authority": "review",
                "mutation_scope": "read_only",
            },
            {
                "ordinal": 2,
                "artifact_kind": "implementation-change",
                "lifecycle_phase": "implementation",
                "authority": "modify",
                "mutation_scope": "workspace_write",
            },
        ),
    )
    assert len(goals) == 2
    assert all(token in goal for goal in goals)
    assert all(".agency-runtime-workspace-write-proof" in goal for goal in goals)
    assert goals[0].endswith("review authority and mutation_scope=read_only.")
    assert goals[1].endswith("modify authority and mutation_scope=workspace_write.")

    long_goals = workforce_work_units_from_descriptors(
        wrapped + " bounded filler" * 1_000,
        (
            {
                "ordinal": 1,
                "artifact_kind": "implementation-change",
                "lifecycle_phase": "implementation",
                "authority": "modify",
                "mutation_scope": "workspace_write",
            },
        ),
    )
    assert len(long_goals[0]) == 4_096
    assert token in long_goals[0]
    assert long_goals[0].endswith("modify authority and mutation_scope=workspace_write.")


def _product_response() -> str:
    return (
        "Agency/Agencies loaded: agency-steward, python-application-engineer, "
        "software-test-engineer\n"
        "Agency/Agencies delegated: python-application-engineer via "
        "generic-worker/spawn_agent, software-test-engineer via "
        "generic-worker/spawn_agent\n"
        "Skills loaded: none - no skill required\n"
        "Actual Model selected: codex-subscription/gpt-5.6-sol\n"
        "Recruited via: inference\n"
        "Why: Two exact product units required implementation and test specialists.\n"
        "How it shaped outcome: Both specialist children completed their exact units.\n\n"
        "The product build completed."
    )


def _two_unit_product_evidence(
    query_hash: str,
    response: str,
    *,
    specs: tuple[tuple[str, str, str], ...] | None = None,
) -> dict[str, object]:
    session_id = "019fa6a6-9432-7c70-a594-68ccdf7e4988"
    trace_id = "product-trace"
    finalization_id = "product-finalization"
    specs = specs or (
        (
            "unit-product-one",
            "python-application-engineer",
            "019fa6a6-a197-7a83-b3fb-d2c20411f608",
        ),
        (
            "unit-product-two",
            "software-test-engineer",
            "019fa6a6-b208-7b94-c40c-e3d315220719",
        ),
    )
    plans: list[dict[str, object]] = []
    delegations: list[dict[str, object]] = []
    grants: list[dict[str, object]] = []
    consumptions: list[dict[str, object]] = []
    workers: list[dict[str, object]] = []
    loads: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    for index, (unit, specialist, receiver_id) in enumerate(specs, start=1):
        goal_hash = hashlib.sha256(f"goal-{index}".encode()).hexdigest()
        prompt_hash = hashlib.sha256(f"prompt-{specialist}".encode()).hexdigest()
        grant_id = f"grant-id-{index}"
        grant_receipt_id = f"grant-receipt-{index}"
        delegation_id = f"delegation-{index}"
        tool_use_id = f"spawn-call-{index}"
        task_name = codex_task_name_for_work_unit(unit)
        tool_evidence = dict.fromkeys(CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS, 0)
        tool_evidence.update(
            {
                "child_tool_call_count": 1,
                "child_function_tool_call_count": 1,
                "child_shell_command_tool_call_count": 1,
                "child_completed_tool_call_count": 1,
                "child_tool_output_count": 1,
            }
        )
        plans.append(
            {
                "work_unit_id": unit,
                "recommended_agent": specialist,
                "goal_hash": goal_hash,
                "delegation_strength": "strongly_preferred",
            }
        )
        grants.append(
            {
                "id": grant_receipt_id,
                "grant_id": grant_id,
                "grant_origin": "native_hook",
                "tool_use_id": tool_use_id,
                "session_id": session_id,
                "trace_id": trace_id,
                "work_unit_id": unit,
                "specialist_slug": specialist,
                "specialist_version": "v1",
                "specialist_prompt_hash": prompt_hash,
                "consumed_at": "2026-07-31T14:00:01Z",
            }
        )
        consumptions.append(
            {
                "grant_id": grant_id,
                "legacy_activation_receipt_id": grant_receipt_id,
                "session_id": session_id,
                "trace_id": trace_id,
                "work_unit_id": unit,
                "specialist_slug": specialist,
                "specialist_version": "v1",
                "specialist_prompt_hash": prompt_hash,
                "worker_id": receiver_id,
                "native_run_id": f"codex-agent:{receiver_id}",
            }
        )
        delegations.append(
            {
                "id": delegation_id,
                "host": "codex",
                "backend": "spawn_agent",
                "work_unit_id": unit,
                "recommended_agent": specialist,
                "status": "completed",
                "activation_receipt_id": grant_receipt_id,
                "retrieved_specialist_slug": specialist,
                "retrieved_specialist_version": "v1",
                "retrieved_specialist_prompt_hash": prompt_hash,
                "executed_worker_id": receiver_id,
                "native_run_id": f"codex-agent:{receiver_id}",
                "completed_at": "2026-07-31T14:01:00Z",
            }
        )
        workers.append(
            {
                "delegation_event_id": delegation_id,
                "backend": "spawn_agent",
                "host": "codex",
                "work_unit_id": unit,
                "worker_id": receiver_id,
                "native_run_id": f"codex-agent:{receiver_id}",
                "started_at": "2026-07-31T14:00:01Z",
                "execution_tool_use_id": f"followup-tool-{index}",
                "execution_dispatched_at": "2026-07-31T14:00:30Z",
                "tool_evidence_schema": CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_SCHEMA,
                "tool_evidence": dict(tool_evidence),
                "tool_evidence_source": "persisted_rollout",
                "tool_evidence_recorded_at": "2026-07-31T14:01:01Z",
                "tool_evidence_status": "recorded",
                "ended_at": "2026-07-31T14:01:00Z",
            }
        )
        if not any(load["agent_slug"] == specialist for load in loads):
            loads.append(
                {
                    "agent_slug": specialist,
                    "activation_receipt_id": grant_receipt_id,
                }
            )
        calls.append(
            {
                "id": f"spawn-item-{index}",
                "event_type": "rollout_call_completed",
                "tool": "spawn_agent",
                "sender_thread_id": session_id,
                "receiver_thread_ids": [receiver_id],
                "status": "completed",
                "prompt_delivery": {
                    "host": "codex",
                    "parent_session_id": session_id,
                    "parent_trace_id": trace_id,
                    "tool_use_id": tool_use_id,
                    "work_unit_id": unit,
                    "specialist_slug": specialist,
                    "specialist_version": "v1",
                    "specialist_prompt_hash": prompt_hash,
                    "goal_hash": goal_hash,
                },
                "execution_delivery": {
                    "work_unit_id": unit,
                    "native_task_name": task_name,
                    "goal_hash": goal_hash,
                },
                "followup_id": f"followup-item-{index}",
                "followup_tool_use_id": f"followup-tool-{index}",
                "native_task_name": task_name,
                "child_status": "completed",
                "activation_completion_count": 1,
                "execution_completion_count": 1,
                "tool_evidence": dict(tool_evidence),
                "evidence_source": "persisted_rollout",
            }
        )
    return {
        "schema": "agency.canary-activation-evidence.v1",
        "proven": True,
        "status": "resolved",
        "reason": "exact_route_resolved",
        "query_hash": query_hash,
        "session_id": session_id,
        "trace_id": trace_id,
        "cardinalities": {
            "routes": 1,
            "runs": 1,
            "traces": 1,
            "unit_agent_plan": len(specs),
            "delegations": len(specs),
            "activation_grants": len(specs),
            "activation_consumptions": len(specs),
            "worker_runs": len(specs),
            "specialist_loads": len(loads),
            "finalizations": 1,
            "preflight_failures": 0,
        },
        "run": {
            "status": "completed",
            "ended_at": "2026-07-31T14:01:01Z",
            "terminal_finalization_id": finalization_id,
        },
        "route": {
            "status": "accepted",
            "query_hash": query_hash,
            "selected_ids": list(dict.fromkeys(item[1] for item in specs)),
            "companion_ids": [],
        },
        "unit_agent_plan": plans,
        "delegations": delegations,
        "activation_grants": grants,
        "activation_consumptions": consumptions,
        "worker_runs": workers,
        "specialist_loads": loads,
        "finalizations": [
            {
                "id": finalization_id,
                "action": "accept",
                "terminal_status": "completed",
                "response_hash": hashlib.sha256(response.encode()).hexdigest(),
            }
        ],
        "collaboration": {
            "schema": "agency.codex-product-collaboration.v2",
            "calls": calls,
            "spawn_count": len(specs),
            "followup_count": len(specs),
            "wait_count": len(specs) * 2,
            "completed_wait_count": len(specs) * 2,
            "timed_out_wait_count": 0,
            "completed_child_count": len(specs),
            "failed_child_count": 0,
            **{
                field: tool_evidence[field] * len(specs)
                for field in CODEX_PRODUCT_CHILD_TOOL_EVIDENCE_FIELDS
            },
            "parent_agent_message_count": 1,
            "unexpected_item_count": 0,
            "host_notice_types": [
                "hook_trust_bypass",
                "skill_catalog_descriptions_shortened",
            ],
            "host_notice_count": 3,
            "evidence_source": "persisted_rollout",
        },
    }


def test_product_proof_rejects_a_child_from_a_different_parent_session() -> None:
    response = _product_response()
    evidence = _two_unit_product_evidence("a" * 64, response)
    collaboration = evidence["collaboration"]
    assert isinstance(collaboration, dict)
    calls = collaboration["calls"]
    assert isinstance(calls, list)
    calls[0]["sender_thread_id"] = "019fa6a6-9432-7c70-a594-68ccdf7e4999"

    failures = codex_product_activation_failures(
        result={"collaboration": collaboration},
        evidence=evidence,
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
    )

    assert "Codex product child did not belong to the exact parent session" in failures


def test_product_proof_rejects_child_tool_evidence_missing_from_store() -> None:
    response = _product_response()
    evidence = _two_unit_product_evidence("a" * 64, response)
    evidence["worker_runs"][0]["tool_evidence"] = None
    evidence["worker_runs"][0]["tool_evidence_schema"] = ""
    evidence["worker_runs"][0]["tool_evidence_source"] = ""
    evidence["worker_runs"][0]["tool_evidence_recorded_at"] = None
    evidence["worker_runs"][0]["tool_evidence_status"] = "missing"

    failures = codex_product_activation_failures(
        result={"collaboration": evidence["collaboration"]},
        evidence=evidence,
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
    )

    assert (
        "Codex product unit unit-product-one child tool evidence was not durably reconciled"
        in failures
    )


def test_product_child_tool_store_write_failure_is_content_free_and_unit_scoped() -> None:
    response = _product_response()
    evidence = _two_unit_product_evidence("a" * 64, response)

    class RejectingStore:
        def record_codex_child_tool_evidence(self, **_record):
            raise ValueError("private backend detail")

    failures = product_host._persist_codex_child_tool_evidence(
        store=RejectingStore(),
        result={"collaboration": evidence["collaboration"]},
        parent_session_id=str(evidence["session_id"]),
    )

    assert failures == (
        "Codex product unit unit-product-one child tool evidence Store write failed",
        "Codex product unit unit-product-two child tool evidence Store write failed",
    )
    assert "private backend detail" not in " ".join(failures)


def test_product_proof_accepts_eight_units_with_one_turn_scoped_specialist_reuse() -> None:
    response = _product_response()
    specialists = (
        "codebase-onboarding-engineer",
        "python-application-engineer",
        "software-test-engineer",
        "technical-writer",
        "code-reviewer",
        "code-reviewer",
        "test-results-analyzer",
        "application-integration-verifier",
    )
    specs = tuple(
        (
            f"unit-product-{index}",
            specialist,
            f"019fa6a6-a{index:03x}-7a83-b3fb-d2c20411f6{index:02x}",
        )
        for index, specialist in enumerate(specialists, start=1)
    )
    evidence = _two_unit_product_evidence("a" * 64, response, specs=specs)
    reviewer_load = next(
        load for load in evidence["specialist_loads"] if load["agent_slug"] == "code-reviewer"
    )
    reviewer_load["activation_receipt_id"] = evidence["activation_grants"][5]["id"]

    failures = codex_product_activation_failures(
        result={"collaboration": evidence["collaboration"]},
        evidence=evidence,
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
    )

    assert failures == ()
    assert evidence["cardinalities"]["unit_agent_plan"] == 8
    assert evidence["cardinalities"]["specialist_loads"] == 7


def test_product_proof_rejects_reused_load_anchored_to_another_specialist() -> None:
    response = _product_response()
    specs = (
        (
            "unit-review-one",
            "code-reviewer",
            "019fa6a6-a001-7a83-b3fb-d2c20411f601",
        ),
        (
            "unit-review-two",
            "code-reviewer",
            "019fa6a6-a002-7a83-b3fb-d2c20411f602",
        ),
        (
            "unit-implementation",
            "python-application-engineer",
            "019fa6a6-a003-7a83-b3fb-d2c20411f603",
        ),
    )
    evidence = _two_unit_product_evidence("a" * 64, response, specs=specs)
    evidence["specialist_loads"][0]["activation_receipt_id"] = evidence["activation_grants"][2][
        "id"
    ]

    failures = codex_product_activation_failures(
        result={"collaboration": evidence["collaboration"]},
        evidence=evidence,
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
    )

    assert "Codex product specialist loads were missing or duplicated" in failures


def test_product_proof_rejects_reuse_across_conflicting_specialist_prompts() -> None:
    response = _product_response()
    specs = (
        (
            "unit-review-one",
            "code-reviewer",
            "019fa6a6-a001-7a83-b3fb-d2c20411f601",
        ),
        (
            "unit-review-two",
            "code-reviewer",
            "019fa6a6-a002-7a83-b3fb-d2c20411f602",
        ),
    )
    evidence = _two_unit_product_evidence("a" * 64, response, specs=specs)
    conflicting_prompt_hash = hashlib.sha256(b"conflicting-reviewer-prompt").hexdigest()
    evidence["activation_grants"][1]["specialist_prompt_hash"] = conflicting_prompt_hash
    evidence["activation_consumptions"][1]["specialist_prompt_hash"] = conflicting_prompt_hash
    evidence["delegations"][1]["retrieved_specialist_prompt_hash"] = conflicting_prompt_hash
    evidence["collaboration"]["calls"][1]["prompt_delivery"]["specialist_prompt_hash"] = (
        conflicting_prompt_hash
    )

    failures = codex_product_activation_failures(
        result={"collaboration": evidence["collaboration"]},
        evidence=evidence,
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
    )

    assert "specialist load was not backed by the consumed activation grant" in failures


def test_product_proof_rejects_parent_side_product_tool_execution() -> None:
    response = _product_response()
    evidence = _two_unit_product_evidence("a" * 64, response)
    collaboration = evidence["collaboration"]
    assert isinstance(collaboration, dict)
    collaboration["unexpected_item_count"] = 1

    failures = codex_product_activation_failures(
        result={"collaboration": collaboration},
        evidence=evidence,
        response_hash=hashlib.sha256(response.encode()).hexdigest(),
    )

    assert "Codex product parent performed a non-collaboration tool call" in failures


@dataclass(frozen=True)
class _Backend:
    observed: dict
    exec_options: tuple[str, ...] | None = None

    def execute(self, *, task: str, workdir: str, check: bool):
        self.observed["invocation"] = {
            "task": task,
            "workdir": workdir,
            "check": check,
            "options": self.exec_options,
        }
        token = next(
            (
                line.strip()
                for line in task.splitlines()
                if line.startswith("agency-runtime-product-write-proof:")
            ),
            "",
        )
        if token:
            (Path(workdir) / ".agency-runtime-workspace-write-proof").write_text(
                token + "\n",
                encoding="utf-8",
            )
        return {
            "backend": "codex",
            "session_id": "019fa6a6-9432-7c70-a594-68ccdf7e4988",
            "profile_scope": "isolated-profile",
            "isolated_plugin": {"registered": True, "enabled": True},
            "status": "completed",
            "exit_code": 0,
            "output": "finished",
            "workspace_trust": _workspace_trust(workdir),
            "trust_mode": "autonomous_bypass",
            "trust_bypass_used": True,
            "persistent_trust_changed": False,
        }


@pytest.mark.parametrize(("mode", "enabled"), (("agency", True), ("native-only", False)))
def test_codex_product_host_uses_isolated_workspace_write_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    enabled: bool,
) -> None:
    observed: dict = {}

    def backend_factory(**kwargs):
        observed["backend_kwargs"] = kwargs
        return _Backend(
            observed,
            exec_options=product_host._codex_options(
                kwargs["model"], agency_mode=kwargs["master_enabled"]
            ),
        )

    monkeypatch.setattr(product_host, "_codex_product_backend", backend_factory)
    monkeypatch.setattr(
        canary,
        "_evidence_delta",
        lambda before, after: {"routing": [], "finalizations": [], "receipts": []},
    )
    monkeypatch.setattr(
        canary,
        "_evidence_summary",
        lambda *_args, **_kwargs: {
            "counts": {},
            "correlated_trace_ids": [],
            "receipt_required": False,
            "receipt_proven": False,
        },
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": mode == "agency"},
        ),
    )
    prompt = "Build the requested product."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode=mode,
        workspace=tmp_path,
        timeout=60,
        model="gpt-test",
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.runtime_contract_passed
    assert result.actual_model == ""
    assert result.requested_model == "gpt-test"
    assert result.response_summary == "nonempty response captured (8 characters)"
    assert observed["backend_kwargs"]["master_enabled"] is enabled
    assert observed["backend_kwargs"]["timeout"] == 60
    assert observed["backend_kwargs"]["model"] == "gpt-test"
    options = observed["invocation"]["options"]
    assert (
        options[options.index("--sandbox")],
        options[options.index("--sandbox") + 1],
    ) == ("--sandbox", "workspace-write")
    assert 'approval_policy="on-request"' in options
    assert 'approvals_reviewer="auto_review"' in options
    assert 'approval_policy="never"' not in options
    assert "danger-full-access" not in options
    assert "--add-dir" not in options
    assert "--ephemeral" not in options
    assert options[options.index("--enable") + 1] == "multi_agent_v2"
    assert "agents.enabled=true" in options
    developer_configs = [
        option.removeprefix("developer_instructions=")
        for option in options
        if option.startswith("developer_instructions=")
    ]
    if enabled:
        assert len(developer_configs) == 1
        assert json.loads(developer_configs[0]) == (
            product_host.CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS
        )
    else:
        assert developer_configs == []
    assert options[-3:] == ("--model", "gpt-test", "-")
    assert observed["invocation"]["workdir"] == str(tmp_path)


def test_codex_agency_product_host_consumes_the_exact_activation_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    class ExactStore:
        def __init__(self, path: Path) -> None:
            observed["db_path"] = path

        def recent_runtime_activity(self, *, limit: int):
            raise AssertionError(f"legacy activity summary was requested with limit={limit}")

        def get_canary_activation_snapshot(self, *, host: str, query_hash: str, session_id: str):
            observed["exact_request"] = (host, query_hash, session_id)
            return {
                "schema": "agency.canary-activation-evidence.v1",
                "proven": True,
                "query_hash": query_hash,
            }

    def backend_factory(**kwargs):
        return _Backend(observed, exec_options=product_host._codex_options(kwargs["model"]))

    def evaluate(_host, *, result, evidence, **_kwargs):
        assert result["status"] == "completed"
        assert evidence["schema"] == "agency.canary-activation-evidence.v1"
        return SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": True},
        )

    monkeypatch.setattr(product_host, "Store", ExactStore)
    monkeypatch.setattr(product_host, "_codex_product_backend", backend_factory)
    monkeypatch.setattr(canary, "_evaluate_proof", evaluate)
    prompt = "Build the exact-snapshot product."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    executed_prompt = str(observed["invocation"]["task"])
    executed_hash = hashlib.sha256(executed_prompt.encode("utf-8")).hexdigest()
    assert observed["exact_request"] == (
        "codex",
        executed_hash,
        "019fa6a6-9432-7c70-a594-68ccdf7e4988",
    )
    assert result.agency_evidence["runtime"]["schema"] == ("agency.canary-activation-evidence.v1")
    assert result.agency_evidence["workspace_trust"]["proven"] is True
    assert result.agency_evidence["hook_trust"] == {
        "schema": "agency.codex-hook-trust-mode.v1",
        "proven": True,
        "trust_mode": "autonomous_bypass",
        "status": "bypassed",
        "persistent_trust_changed": False,
    }
    assert result.workspace_write_proven is True
    assert not (tmp_path / ".agency-runtime-workspace-write-proof").exists()


def test_codex_agency_product_host_requires_native_parent_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    @dataclass(frozen=True)
    class MissingSessionBackend(_Backend):
        def execute(self, *, task: str, workdir: str, check: bool):
            record = super().execute(task=task, workdir=workdir, check=check)
            record.pop("session_id")
            return record

    monkeypatch.setattr(
        product_host,
        "_codex_product_backend",
        lambda **_kwargs: MissingSessionBackend(observed),
    )
    prompt = "Build the exact-session product."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.status == "failed"
    assert result.runtime_contract_passed is False
    assert result.error == "runtime evidence reconciliation failed: ValueError"


def test_codex_product_host_uses_unmocked_multi_unit_product_proof(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}
    response = _product_response()

    class ExactStore:
        def __init__(self, path: Path) -> None:
            observed["db_path"] = path

        def recent_runtime_activity(self, *, limit: int):
            raise AssertionError(f"legacy activity summary was requested with limit={limit}")

        def record_codex_child_tool_evidence(self, **record):
            observed.setdefault("stored_tool_evidence", []).append(record)
            return record

        def get_canary_activation_snapshot(self, *, host: str, query_hash: str, session_id: str):
            observed["exact_request"] = (host, query_hash, session_id)
            evidence = dict(observed["evidence"])
            assert evidence["query_hash"] == query_hash
            evidence.pop("collaboration")
            return evidence

    @dataclass(frozen=True)
    class ProductBackend(_Backend):
        def execute(self, *, task: str, workdir: str, check: bool):
            record = super().execute(task=task, workdir=workdir, check=check)
            evidence = _two_unit_product_evidence(
                hashlib.sha256(task.encode()).hexdigest(), response
            )
            observed["evidence"] = evidence
            record["output"] = response
            record["collaboration"] = evidence["collaboration"]
            record["collaboration"]["private_parent_prompt"] = "do-not-persist-parent"
            record["collaboration"]["calls"][0]["private_child_message"] = "do-not-persist-child"
            record["collaboration"]["private_host_notice_message"] = "do-not-persist-notice"
            return record

    monkeypatch.setattr(product_host, "Store", ExactStore)
    monkeypatch.setattr(
        product_host,
        "_codex_product_backend",
        lambda **kwargs: ProductBackend(
            observed,
            exec_options=product_host._codex_options(kwargs["model"]),
        ),
    )
    prompt = "Build the exact two-unit product."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=600,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.runtime_contract_passed is True, result.error
    assert result.agency_evidence["proof"]["activation_contract"] == "product"
    assert result.agency_evidence["proof"]["correction_count"] == 0
    assert result.agency_evidence["proof"]["collaboration"]["spawn_count"] == 2
    assert result.agency_evidence["proof"]["collaboration"]["host_notice_types"] == [
        "hook_trust_bypass",
        "skill_catalog_descriptions_shortened",
    ]
    assert result.agency_evidence["proof"]["collaboration"]["host_notice_count"] == 3
    assert result.actual_model == "codex-subscription/gpt-5.6-sol"
    assert result.workspace_write_proven is True
    stored_tool_evidence = observed["stored_tool_evidence"]
    assert isinstance(stored_tool_evidence, list)
    assert len(stored_tool_evidence) == 2
    assert {str(item["work_unit_id"]) for item in stored_tool_evidence} == {
        "unit-product-one",
        "unit-product-two",
    }
    serialized_evidence = json.dumps(result.agency_evidence, sort_keys=True)
    assert "do-not-persist-parent" not in serialized_evidence
    assert "do-not-persist-child" not in serialized_evidence
    assert "do-not-persist-notice" not in serialized_evidence


@pytest.mark.parametrize(
    ("host_notice_types", "host_notice_count"),
    [
        (["unknown_notice"], 1),
        (["hook_trust_bypass", "hook_trust_bypass"], 2),
        (["hook_trust_bypass"], True),
        (["hook_trust_bypass"], 0),
        ([], 1),
        (["hook_trust_bypass"], 5_001),
        ("hook_trust_bypass", 1),
    ],
)
def test_product_collaboration_projection_rejects_invalid_host_notice_evidence(
    host_notice_types: object,
    host_notice_count: object,
) -> None:
    response = _product_response()
    evidence = _two_unit_product_evidence("a" * 64, response)
    collaboration = evidence["collaboration"]
    assert isinstance(collaboration, dict)
    collaboration["host_notice_types"] = host_notice_types
    collaboration["host_notice_count"] = host_notice_count

    assert (
        _codex_product_collaboration_projection(
            {"collaboration": collaboration},
            expected_parent_thread_id=str(evidence["session_id"]),
        )
        is None
    )
    proof = canary._evaluate_proof(
        "codex",
        result={
            "backend": "codex",
            "profile_scope": "current-profile",
            "status": "completed",
            "exit_code": 0,
            "output": response,
            "collaboration": collaboration,
        },
        evidence=evidence,
        default_profile_scope="current-profile",
        mode="agency",
        activation_contract="product",
    )

    assert proof.invocation["collaboration"] is None
    assert proof.passed is False
    assert "Codex product collaboration projection was missing or invalid" in proof.failures


def test_codex_product_backend_trusts_only_the_isolated_trial_workspace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_home = tmp_path / "source-home"
    source_codex = source_home / ".codex"
    source_codex.mkdir(parents=True)
    (source_codex / "auth.json").write_text("{}", encoding="utf-8")
    persistent_config = source_codex / "config.toml"
    persistent_bytes = b"[projects.'persistent']\ntrust_level = \"trusted\"\n"
    persistent_config.write_bytes(persistent_bytes)
    workspace = tmp_path / "trial-workspace"
    workspace.mkdir()
    marketplace = tmp_path / "marketplace"
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    isolated_configs: list[str] = []
    setup_environments: list[dict[str, str]] = []
    execution_environments: list[dict[str, str]] = []
    execution_argv: list[list[str]] = []
    rollout_projection: dict[str, object] = {}

    def project_record(_result, **kwargs):
        rollout_projection.update(kwargs)
        return {
            "backend": "codex",
            "profile_scope": "isolated-profile",
            "status": "completed",
            "exit_code": 0,
            "output": "done",
        }

    monkeypatch.setattr(canary, "_codex_canary_record", project_record)

    def runner(argv, *, cwd, env, input_text=None, **_kwargs):
        config = Path(env["CODEX_HOME"]) / "config.toml"
        isolated_configs.append(config.read_text(encoding="utf-8"))
        if argv[1:3] == ["plugin", "list"]:
            return BoundedProcessResult(
                0,
                json.dumps(
                    {
                        "plugins": [
                            {
                                "pluginId": "agency-preflight@agency-runtime",
                                "installed": True,
                                "enabled": True,
                            }
                        ]
                    }
                ),
                "",
            )
        if "exec" in argv:
            execution_argv.append(list(argv))
            execution_environments.append(dict(env))
            stdout = "\n".join(
                (
                    json.dumps(
                        {
                            "type": "thread.started",
                            "thread_id": "00000000-0000-0000-0000-000000000001",
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"id": "message", "type": "agent_message", "text": "done"},
                        }
                    ),
                    json.dumps({"type": "turn.completed"}),
                )
            )
            return BoundedProcessResult(0, stdout, "")
        setup_environments.append(dict(env))
        return BoundedProcessResult(0, "{}", "")

    backend = product_host._codex_product_backend(
        native={"managed_target": str(marketplace)},
        db_path=tmp_path / "agency.db",
        timeout=60,
        master_enabled=True,
        model="",
        resolver=lambda _host: "codex",
        runner=runner,
        environ={"HOME": str(source_home), "PATH": ""},
        workspace=workspace,
    )

    result = backend.execute(task="build", workdir=str(workspace), check=False)

    expected = str(workspace.resolve())
    if os.name == "nt":
        expected = expected.casefold()
    assert result["status"] == "completed"
    assert result["workspace_trust"] == _workspace_trust(str(workspace))
    assert isolated_configs
    parsed = tomllib.loads(isolated_configs[0])
    assert parsed == {"projects": {expected: {"trust_level": "trusted"}}}
    assert persistent_config.read_bytes() == persistent_bytes
    assert execution_environments
    assert setup_environments
    assert all(
        len({environment[name] for name in ("TEMP", "TMP", "TMPDIR")}) == 1
        and environment["TEMP"] != str(workspace.resolve())
        for environment in setup_environments
    )
    assert "--dangerously-bypass-hook-trust" in execution_argv[0]
    assert 'approval_policy="on-request"' in execution_argv[0]
    assert 'approvals_reviewer="auto_review"' in execution_argv[0]
    assert 'approval_policy="never"' not in execution_argv[0]
    assert result["trust_mode"] == "autonomous_bypass"
    assert result["trust_bypass_used"] is True
    assert result["persistent_trust_changed"] is False
    assert execution_environments[0]["AGENCY_CANARY_REQUIRE_EXISTING_STORE"] == "1"
    assert execution_environments[0]["AGENCY_CODEX_HOOK_EVENT_DIAGNOSTICS"] == "1"
    assert {execution_environments[0][name] for name in ("TEMP", "TMP", "TMPDIR")} == {
        str(workspace.resolve())
    }
    assert Path(rollout_projection["rollout_root"]) == (
        Path(execution_environments[0]["CODEX_HOME"]) / "sessions"
    )
    assert rollout_projection["rollout_not_before"] is not None
    assert rollout_projection["rollout_not_after"] is not None


def test_product_host_reports_missing_workspace_write_proof_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict = {}

    @dataclass(frozen=True)
    class NoWriteBackend(_Backend):
        def execute(self, *, task: str, workdir: str, check: bool):
            self.observed["invocation"] = {"task": task, "workdir": workdir, "check": check}
            return {
                "backend": "codex",
                "session_id": "019fa6a6-9432-7c70-a594-68ccdf7e4988",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {"registered": True, "enabled": True},
                "status": "completed",
                "exit_code": 0,
                "output": "finished",
                "workspace_trust": _workspace_trust(workdir),
            }

    monkeypatch.setattr(
        product_host,
        "_codex_product_backend",
        lambda **_kwargs: NoWriteBackend(observed),
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": True},
        ),
    )
    prompt = "Build but fail the write proof."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.status == "completed"
    assert result.workspace_write_proven is False
    assert not result.runtime_contract_passed
    assert result.agency_evidence["workspace_write"]["reason"] == "proof_file_missing"
    assert "workspace_write_not_proven" in result.error


def test_product_host_requires_exact_workspace_trust_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict = {}

    @dataclass(frozen=True)
    class NoTrustBackend(_Backend):
        def execute(self, *, task: str, workdir: str, check: bool):
            record = super().execute(task=task, workdir=workdir, check=check)
            record.pop("workspace_trust")
            return record

    monkeypatch.setattr(
        product_host,
        "_codex_product_backend",
        lambda **_kwargs: NoTrustBackend(observed),
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": True},
        ),
    )
    prompt = "Build without trust evidence."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.workspace_write_proven is True
    assert not result.runtime_contract_passed
    assert result.agency_evidence["workspace_trust"] == {
        "schema": "agency.codex-isolated-workspace-trust.v1",
        "proven": False,
        "status": "unproven",
        "scope": "exact-workspace",
        "workspace_hash": _workspace_trust(str(tmp_path))["workspace_hash"],
        "persistent_profile_changed": None,
        "reason": "workspace_trust_evidence_missing_or_mismatched",
    }
    assert "workspace_trust_not_proven" in result.error


def test_product_host_rejects_a_preexisting_write_proof(
    tmp_path: Path,
) -> None:
    proof = tmp_path / ".agency-runtime-workspace-write-proof"
    proof.write_text("agency-runtime-product-write-proof:spoofed\n", encoding="utf-8")
    prompt = "Build without accepting spoofed evidence."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: pytest.fail("inspection ran after preexisting proof"),
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.status == "failed"
    assert result.workspace_write_proven is False
    assert not result.runtime_contract_passed
    assert result.error == "safe product backend preparation failed: ValueError"
    assert proof.read_text(encoding="utf-8") == ("agency-runtime-product-write-proof:spoofed\n")


def test_codex_product_backend_persists_parent_and_correlates_exact_rollout(
    tmp_path: Path,
) -> None:
    marketplace = tmp_path / "marketplace"
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")

    backend = product_host._codex_product_backend(
        native={"managed_target": str(marketplace)},
        db_path=tmp_path / "agency.db",
        timeout=60,
        master_enabled=True,
        model="",
        resolver=lambda _host: "codex",
        runner=None,
        environ={"HOME": str(tmp_path), "PATH": ""},
        workspace=tmp_path,
    )

    assert "--ephemeral" not in backend.exec_options
    assert backend.exec_options[backend.exec_options.index("--enable") + 1] == "multi_agent_v2"
    assert "agents.enabled=true" in backend.exec_options
    developer_configs = [
        option.removeprefix("developer_instructions=")
        for option in backend.exec_options
        if option.startswith("developer_instructions=")
    ]
    assert developer_configs == [json.dumps(product_host.CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS)]
    assert backend.require_existing_store is True
    assert backend.hook_event_diagnostics is True
    assert backend.require_exact_activation_rollout is True
    assert backend.rollout_contract == "product"
    assert backend.trust_mode == "autonomous_bypass"
    assert backend.project_agency_global_guidance is True


def test_codex_product_backend_supplies_bounded_parent_and_child_delegation_authority(
    tmp_path: Path,
) -> None:
    marketplace = tmp_path / "marketplace"
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")

    backend = product_host._codex_product_backend(
        native={"managed_target": str(marketplace)},
        db_path=tmp_path / "agency.db",
        timeout=60,
        master_enabled=True,
        model="",
        resolver=lambda _host: "codex",
        runner=None,
        environ={"HOME": str(tmp_path), "PATH": ""},
        workspace=tmp_path,
    )

    developer_configs = [
        option.removeprefix("developer_instructions=")
        for option in backend.exec_options
        if option.startswith("developer_instructions=")
    ]
    assert len(developer_configs) == 1
    instructions = json.loads(developer_configs[0])
    assert instructions == product_host.CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS
    for required_contract in (
        "[AGENCY EXACT SPECIALIST EXECUTION v3]",
        "[AGENCY EXACT SPECIALIST ACTIVATION v1]",
        "[AGENCY EXACT TASK EXECUTION v1]",
        "[AGENCY DELEGATION PLAN]",
        "spawn_agent",
        "followup_task",
        "wait_agent",
        "fork_turns",
        "native_task_name",
        "depends_on",
        "one child at a time",
        "Use no non-collaboration tools",
        "do not delegate further",
        "executes in that initial child turn",
        "Do not call followup_task",
        "accepted plan and native activation already prove the required host tools",
        "current working directory is the exact isolated product workspace",
        "permitted workspace tools for every required implementation",
        "successful workspace-local patch receipt before any final response",
        "proof-only named-file change is a legitimate implementation unit",
        "timeout_ms=120000",
        "repeat that same wait up to two additional times",
        "Never spawn the next row until",
    ):
        assert required_contract in instructions


def test_product_host_rejects_unsupported_hosts_and_prompt_drift(tmp_path: Path) -> None:
    prompt = "Build."
    with pytest.raises(ValueError, match="no proven isolated workspace-write"):
        execute_product_host(
            prompt=prompt,
            prompt_hash=_hash(prompt),
            host="openclaw",
            mode="agency",
            workspace=tmp_path,
            timeout=60,
        )
    with pytest.raises(ValueError, match="prompt hash"):
        execute_product_host(
            prompt=prompt,
            prompt_hash="sha256:" + ("0" * 64),
            host="codex",
            mode="agency",
            workspace=tmp_path,
            timeout=60,
        )


def test_product_host_returns_bounded_failure_without_fabricating_evidence(
    tmp_path: Path,
) -> None:
    prompt = "Build."

    def failed_inspector(_host: str):
        raise RuntimeError("secret detail must not cross the boundary")

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=failed_inspector,
    )

    assert result.status == "failed"
    assert not result.runtime_contract_passed
    assert result.agency_evidence == {}
    assert result.actual_model == ""
    assert "RuntimeError" in result.error
    assert "secret detail" not in result.error
