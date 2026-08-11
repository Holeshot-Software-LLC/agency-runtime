"""Curated mutation proof for Agency's load-bearing runtime decisions.

The evaluator never mutates the requested checkout. It copies the minimum
repository inputs into an owner-private disposable directory, proves the named
tests are green there, and then creates a fresh copy for each exact mutation.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.private_paths import private_temporary_directory
from agency_runtime.core.process_environment import least_privilege_subprocess_environment

SCHEMA: Final[str] = "agency-runtime.decision-conformance"
VERSION: Final[int] = 1
DEFAULT_TIMEOUT_SECONDS: Final[float] = 90.0
_COPY_SUPPORT = (
    "conftest.py",
    "runtime_support.py",
    "test_product_validation.py",
    "__init__.py",
)


@dataclass(frozen=True, slots=True)
class DecisionMutation:
    mutation_id: str
    invariant: str
    source_path: str
    before: str
    after: str
    test_node: str


@dataclass(frozen=True, slots=True)
class _PytestRun:
    exit_code: int | None
    failed_nodes: tuple[str, ...]
    duration_ms: int
    timed_out: bool = False
    failure_excerpt: str | None = None


MUTATIONS: Final[tuple[DecisionMutation, ...]] = (
    DecisionMutation(
        mutation_id="configured-provider-bypasses-inference",
        invariant="A configured provider always owns online planning and specialist selection.",
        source_path="agency_runtime/core/workforce/inference.py",
        before="    if not _inference_declared(config):",
        after="    if _inference_declared(config):",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_balanced_mode_always_uses_inference_for_planning_and_selection"
        ),
    ),
    DecisionMutation(
        mutation_id="missing-provider-restores-offline-staffing",
        invariant="Missing inference fails without a deterministic specialist team.",
        source_path="agency_runtime/core/workforce/inference.py",
        before="""    if not _inference_declared(config):
        return _inference_failure(
            mode=mode,
            configured=False,
            plan=None,
            proposal=None,
            attempts=(),
            detail_codes=("workforce_provider_unavailable",),
            calls_used=0,
        )""",
        after="""    if not _inference_declared(config):
        from agency_runtime.core.workforce.fallback import deterministic_plan_and_staff

        offline = deterministic_plan_and_staff(
            request,
            snapshot,
            config=config,
            context=context,
        )
        return WorkforceRoutingOutcome(
            status="accepted",
            mode=mode,
            inference_mode="deterministic",
            plan=offline.plan,
            proposal=offline.proposal,
            staffing=offline.staffing,
            attempts=(),
            abstention_codes=(),
            calls_used=0,
            decision_source="deterministic",
        )""",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_no_provider_declines_without_selecting_or_calling_the_model"
        ),
    ),
    DecisionMutation(
        mutation_id="online-plan-restores-deterministic-enrichment",
        invariant="Production planning preserves the inference-authored plan without local additions.",
        source_path="agency_runtime/core/workforce/inference.py",
        before="""    return primary


def _typed_shortlists(""",
        after="""    from agency_runtime.core.workforce.intent import enrich_intent_plan

    return enrich_intent_plan(primary, request=request, context=context)


def _typed_shortlists(""",
        test_node=(
            "tests/test_workforce_selection_safety.py::"
            "test_production_staffing_entrypoints_have_no_deterministic_decider_dependency"
        ),
    ),
    DecisionMutation(
        mutation_id="planner-drops-deterministic-acceptance-contract",
        invariant=(
            "Inference receives the exact deterministic plan acceptance contract before it "
            "authors a plan."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before='                "plan_acceptance_contract": planner_acceptance_contract(),',
        after='                "plan_acceptance_contract": {},',
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_planner_repair_receives_exact_assurance_graph_and_remains_inference_owned"
        ),
    ),
    DecisionMutation(
        mutation_id="unit-assignment-reinterprets-unavailable-inference",
        invariant="An unavailable inference route cannot become an exact unit recommendation.",
        source_path="agency_runtime/core/unit_assignment.py",
        before='    if inference_mode not in {"inferred", "durable_reuse", "cached"}:',
        after=(
            '    if inference_mode not in {"inferred", "durable_reuse", "cached", "unavailable"}:'
        ),
        test_node=(
            "tests/test_unit_assignment_selector.py::"
            "test_unavailable_inference_cannot_be_reinterpreted_as_a_unit_assignment"
        ),
    ),
    DecisionMutation(
        mutation_id="unconfigured-child-preserves-specialist-selection",
        invariant="An unconfigured child route clears every unproven specialist identity.",
        source_path="agency_runtime/core/preflight.py",
        before="""            selected_ids=[],
            semantic_ids=[],
            status="inference_unavailable",""",
        after="""            selected_ids=list(routing.get("selected_ids", [])),
            semantic_ids=list(routing.get("semantic_ids", [])),
            status="inference_unavailable",""",
        test_node=(
            "tests/test_child_routing_coordination.py::"
            "test_child_owner_failure_aborts_and_unconfigured_child_fails_closed"
        ),
    ),
    DecisionMutation(
        mutation_id="resident-steward-restores-imported-default-pair",
        invariant=(
            "Exactly one Agency-native steward is resident; imported managers remain optional "
            "specialists."
        ),
        source_path="agency_runtime/core/resident_managers.py",
        before=('RESIDENT_MANAGER_SLUGS: Final[tuple[str, ...]] = ("agency-steward",)'),
        after=(
            "RESIDENT_MANAGER_SLUGS: Final[tuple[str, ...]] = "
            '("agents-orchestrator", "chief-of-staff")'
        ),
        test_node=(
            "tests/test_resident_managers.py::"
            "test_resident_identity_is_canonical_and_compatibility_aliases_share_it"
        ),
    ),
    DecisionMutation(
        mutation_id="implicit-staffing-failure-becomes-hiring-gap",
        invariant=(
            "An online staff decision without a safe team is repaired by inference rather "
            "than relabeled as a contractor gap."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before="""        if decision == "staff" and not proposal_row.selected:
            failures.append(_NominationFailure(unit.unit_id, "staff_without_safe_team"))""",
        after="""        if decision == "staff" and not proposal_row.selected:
            continue""",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_staff_decision_without_safe_team_gets_one_bounded_inference_repair"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-validation-drops-later-unit-failures",
        invariant=(
            "One bounded recruiter repair receives every invalid planned unit, not only the first."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before="""    if failures:
        raise _NominationValidationError(failures)


@dataclass(slots=True)
class _NominationSemantics:""",
        after="""    if failures:
        raise _NominationValidationError(failures[:1])


@dataclass(slots=True)
class _NominationSemantics:""",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_recruiter_repair_receives_every_invalid_unit_and_preserves_valid_rows"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-gap-requires-invented-roster-candidate",
        invariant=(
            "Recruiter inference may declare a real gap with zero ranked roster candidates."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before='            or (decision == "staff" and not raw_ranks)',
        after="            or not raw_ranks",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_open_ended_pool_can_declare_gap_without_inventing_a_roster_candidate"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-repair-restores-full-plan-system-contract",
        invariant=(
            "A partial recruiter repair receives a non-contradictory system contract that "
            "requests only failed planned units."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before="        repair_system_prompt=_RECRUITER_REPAIR_SYSTEM,",
        after="        repair_system_prompt=_RECRUITER_SYSTEM,",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_balanced_recruiter_repairs_only_missing_work_unit_rows"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-drops-typed-recall-evidence",
        invariant=(
            "Recruiter inference receives exact non-ranked typed coverage and uncovered-gap "
            "evidence for every planned unit."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before='            "typed_recall": typed_recall,',
        after='            "typed_recall": [],',
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_recruiter_repair_declares_gap_when_typed_recall_proves_uncovered_requirements"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-repair-allows-unlisted-row-overwrite",
        invariant=(
            "A recruiter repair must match the ordered failed-unit set before it can "
            "replace any accumulated row."
        ),
        source_path="agency_runtime/core/workforce/inference.py",
        before="""        if self._repair_unit_ids and tuple(response_ids) != self._repair_unit_ids:
            raise ValueError("workforce nomination repair rows do not match failed units")""",
        after="""        if False and self._repair_unit_ids and tuple(response_ids) != self._repair_unit_ids:
            raise ValueError("workforce nomination repair rows do not match failed units")""",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_recruiter_repair_rejects_rows_outside_recorded_failure_set"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-failure-detail-dropped-from-durable-receipt",
        invariant=(
            "A durable route retains only the allowlisted unit and reason codes needed to "
            "diagnose a recruiter rejection."
        ),
        source_path="agency_runtime/core/selector/receipt_projection.py",
        before="""        if validation_failures:
            attempt["validation_failures"] = validation_failures""",
        after="""        if False and validation_failures:
            attempt["validation_failures"] = validation_failures""",
        test_node=(
            "tests/test_routing_receipt_header.py::"
            "test_routing_receipt_is_bounded_content_free_and_idempotent"
        ),
    ),
    DecisionMutation(
        mutation_id="recruiter-failure-sensitive-unit-id-not-sanitized",
        invariant=("A durable recruiter failure hashes a sensitive planner-derived unit identity."),
        source_path="agency_runtime/core/selector/receipt_projection.py",
        before="""        projected_unit_id = _identity(unit_id)
        failure = {"unit_id": projected_unit_id, "reason_code": reason_code}""",
        after="""        projected_unit_id = unit_id
        failure = {"unit_id": projected_unit_id, "reason_code": reason_code}""",
        test_node=(
            "tests/test_routing_receipt_header.py::"
            "test_routing_receipt_is_bounded_content_free_and_idempotent"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-falls-back-to-legacy-activity-summary",
        invariant=(
            "Codex Agency product trials consume the exact activation snapshot for the "
            "executed prompt hash and native parent session."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="""        if normalized_host == "codex" and normalized_mode == "agency":
            session_id = validate_correlation_id(
                str(result.get("session_id") or ""),
                field="session_id",
            )
            tool_evidence_store_failures = _persist_codex_child_tool_evidence(
                store=store,
                result=result,
                parent_session_id=session_id,
            )
            evidence = store.get_canary_activation_snapshot(
                host=normalized_host,
                query_hash=executed_prompt_hash.removeprefix("sha256:"),
                session_id=session_id,
            )""",
        after="""        if normalized_host == "codex" and normalized_mode == "agency":
            session_id = validate_correlation_id(
                str(result.get("session_id") or ""),
                field="session_id",
            )
            tool_evidence_store_failures = _persist_codex_child_tool_evidence(
                store=store,
                result=result,
                parent_session_id=session_id,
            )
            evidence = store.recent_runtime_activity(limit=500)""",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_agency_product_host_consumes_the_exact_activation_snapshot"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-drops-exact-codex-session-binding",
        invariant=(
            "Repeated product prompts resolve only against the exact native Codex parent session."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="""            evidence = store.get_canary_activation_snapshot(
                host=normalized_host,
                query_hash=executed_prompt_hash.removeprefix("sha256:"),
                session_id=session_id,
            )""",
        after="""            evidence = store.get_canary_activation_snapshot(
                host=normalized_host,
                query_hash=executed_prompt_hash.removeprefix("sha256:"),
            )""",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_agency_product_host_consumes_the_exact_activation_snapshot"
        ),
    ),
    DecisionMutation(
        mutation_id="activation-canary-accepts-no-inference-attempt",
        invariant=(
            "The Codex activation canary cannot select a worker without a recorded inference "
            "attempt."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before='        (routing.get("inference_attempted") is True, "inference_attempted"),',
        after='        (True, "inference_attempted"),',
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_activation_canary_rejects_missing_inference_attempt_evidence"
        ),
    ),
    DecisionMutation(
        mutation_id="activation-canary-accepts-no-provider-receipt",
        invariant=(
            "The Codex activation canary cannot select a worker without a nonempty provider "
            "attempt receipt."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before="""            isinstance(routing.get("provider_attempts"), list)
            and bool(routing["provider_attempts"]),""",
        after="""            isinstance(routing.get("provider_attempts"), list)
            and True,""",
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_activation_canary_rejects_missing_provider_attempt_receipts"
        ),
    ),
    DecisionMutation(
        mutation_id="activation-canary-enters-gap-hiring",
        invariant="The read-only Codex activation canary cannot enter gap hiring.",
        source_path="agency_runtime/core/selector/pipeline.py",
        before="        if activation_canary:\n            hiring_events = []",
        after="        if False:\n            hiring_events = []",
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_activation_canary_uses_inference_owned_selection"
        ),
    ),
    DecisionMutation(
        mutation_id="product-canary-suppresses-gap-hiring",
        invariant=(
            "An ordinary product task may hire an inference-declared specialist gap even when "
            "its isolated hook requires the existing Store."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before="""    from agency_runtime.core.roster.workforce import (
        workforce_index_snapshot,
        workforce_snapshot_with_contract,
    )""",
        after="""    from agency_runtime.core.codex_activation_verification import (
        is_restricted_codex_activation_canary_environment,
    )

    if is_restricted_codex_activation_canary_environment():
        return outcome, active_snapshot, active_catalog, []

    from agency_runtime.core.roster.workforce import (
        workforce_index_snapshot,
        workforce_snapshot_with_contract,
    )""",
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_existing_store_product_canary_can_hire_an_inference_declared_gap"
        ),
    ),
    DecisionMutation(
        mutation_id="persistent-host-restores-legacy-context-ceiling",
        invariant=(
            "Persistent native parents may carry the complete bounded specialist team and "
            "delegation plan up to the general preflight ceiling."
        ),
        source_path="agency_runtime/core/preflight_recipe.py",
        before="PERSISTENT_HOST_CONTEXT_CHARS = MAX_PREFLIGHT_CONTEXT_CHARS",
        after="PERSISTENT_HOST_CONTEXT_CHARS = 8_192",
        # Re-anchored twice. The isolated-delivery test this originally named
        # was deleted with that mode; the first re-anchor picked a ceiling test
        # that expresses its sizes as `PERSISTENT_HOST_CONTEXT_CHARS + 1` and
        # therefore stays self-consistent for ANY value of the constant -- it
        # could never kill this mutation, and did not. Now anchored to the
        # equality itself, which is the invariant.
        test_node=(
            "tests/test_preflight_bounds.py::"
            "test_persistent_host_ceiling_is_the_general_preflight_ceiling"
        ),
    ),
    DecisionMutation(
        mutation_id="persistent-host-drops-encoded-output-bound",
        invariant=(
            "Persistent native-parent context is rejected before ready commit when its exact "
            "UTF-8 hook envelope exceeds the reserved output budget."
        ),
        source_path="agency_runtime/core/preflight_recipe.py",
        before=(
            "    if _persistent_host_context_output_bytes(context) "
            "> PERSISTENT_HOST_CONTEXT_OUTPUT_BYTES:"
        ),
        after=(
            "    if False and _persistent_host_context_output_bytes(context) "
            "> PERSISTENT_HOST_CONTEXT_OUTPUT_BYTES:"
        ),
        test_node=(
            "tests/test_preflight_bounds.py::"
            "test_multibyte_complete_context_fails_before_ready_is_persisted"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-user-prompt-admits-oversized-model-header",
        invariant=(
            "Codex rejects an oversized UTF-8 model identifier before preflight can commit "
            "a route whose appended evidence header exceeds the final hook envelope."
        ),
        source_path="agency_runtime/adapters/hooks.py",
        before=(
            "        model = _bounded_optional_utf8_string(\n"
            "            payload,\n"
            '            "model",\n'
            "            maximum_bytes=MAX_HOOK_MODEL_BYTES,\n"
            "        )"
        ),
        after='        model = _optional_string(payload, "model")',
        test_node=(
            "tests/test_host_hooks.py::"
            "test_codex_rejects_oversized_utf8_model_before_preflight_ready"
        ),
    ),
    DecisionMutation(
        mutation_id="ready-routing-receipt-restores-legacy-node-cap",
        invariant=(
            "Ready routing receipts accept every structurally bounded decision admitted by "
            "the durable preflight recipe."
        ),
        source_path="agency_runtime/core/store/preflight.py",
        before="""def _routing_component_matches(
    conn: Any,
    *,
    session_id: str,
    trace_id: str,
    routing: dict[str, Any],
) -> bool:
    rows = conn.execute(
        "SELECT query_hash, context_fingerprint, source, decision "
        "FROM routing_decisions WHERE session_id = ? AND trace_id = ? ORDER BY id",
        (session_id, trace_id),
    ).fetchall()
    if len(rows) != 1:
        return False
    row = rows[0]
    try:
        decision = safe_load_bounded_json(
            str(row["decision"] or ""),
            maximum_bytes=64_000,
            maximum_depth=8,
            maximum_nodes=_MAX_RECIPE_NODES,
        )""",
        after="""def _routing_component_matches(
    conn: Any,
    *,
    session_id: str,
    trace_id: str,
    routing: dict[str, Any],
) -> bool:
    rows = conn.execute(
        "SELECT query_hash, context_fingerprint, source, decision "
        "FROM routing_decisions WHERE session_id = ? AND trace_id = ? ORDER BY id",
        (session_id, trace_id),
    ).fetchall()
    if len(rows) != 1:
        return False
    row = rows[0]
    try:
        decision = safe_load_bounded_json(
            str(row["decision"] or ""),
            maximum_bytes=64_000,
            maximum_depth=8,
            maximum_nodes=256,
        )""",
        test_node=(
            "tests/test_routing_receipt_header.py::"
            "test_ready_receipt_accepts_valid_routing_above_legacy_node_limit"
        ),
    ),
    DecisionMutation(
        mutation_id="activation-canary-allows-plan-subdivision",
        invariant=(
            "The exact indivisible Codex activation request constrains inference to one planned "
            "work unit."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before='                "max_planned_units": 1,',
        after='                "max_planned_units": 2,',
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_activation_canary_uses_inference_owned_selection"
        ),
    ),
    DecisionMutation(
        mutation_id="activation-canary-allows-wrong-artifact",
        invariant=(
            "The exact Codex review canary constrains inference to the requested review-report "
            "artifact."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before='                "required_planned_artifact_kind": "review-report",',
        after='                "required_planned_artifact_kind": "analysis",',
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_activation_canary_uses_inference_owned_selection"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-restores-ephemeral-parent",
        invariant=(
            "Ordinary Codex product trials persist the parent turn required by native "
            "multi-agent delegation."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="""    "never",
    "--ignore-rules",""",
        after="""    "never",
    "--ephemeral",
    "--ignore-rules",""",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-disables-multi-agent-v2",
        invariant="Ordinary Codex product trials explicitly enable native multi-agent V2.",
        source_path="agency_runtime/core/evals/product_host.py",
        before='    "multi_agent_v2",',
        after='    "multi_agent_v1",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-disables-agents",
        invariant="Ordinary Codex product trials explicitly enable the agents capability.",
        source_path="agency_runtime/core/evals/product_host.py",
        before='    "agents.enabled=true",',
        after='    "agents.enabled=false",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-drops-explicit-delegation-authority",
        invariant=(
            "Codex product trials give the parent exact scheduling mechanics for every "
            "accepted plan row and prevent delegated children from recursively spawning."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before=(
            '    f"developer_instructions={json.dumps(CODEX_PRODUCT_DEVELOPER_INSTRUCTIONS)}",'
        ),
        after='    "developer_instructions=\\"\\"",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_supplies_bounded_parent_and_child_delegation_authority"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-advances-after-commentary-wake",
        invariant=("A product parent never advances after a nonterminal child commentary wake."),
        source_path="agency_runtime/core/evals/product_host.py",
        before=(
            '    "timeout_ms=120000. A nonterminal commentary update is not completion: repeat that "'
        ),
        after=('    "timeout_ms=120000. Advance after the first nonterminal commentary update. "'),
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_supplies_bounded_parent_and_child_delegation_authority"
        ),
    ),
    DecisionMutation(
        mutation_id="product-rollout-rejects-commentary-waits",
        invariant=(
            "Product rollout evidence admits bounded repeated execution waits before terminal child completion."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before=("    maximum_waits = len(spawns) * 3 if direct_mode else len(spawns) * 4\n"),
        after="    maximum_waits = len(spawns)\n",
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_product_rollout_projects_exact_eight_unit_reuse_topology"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-global-guidance-drops-native-delegation-request",
        invariant=(
            "A Codex installation explicitly requests native delegation only for an "
            "accepted current-turn Agency plan."
        ),
        source_path="agency_runtime/core/codex_global_guidance.py",
        before="owner configuration explicitly requests Codex native subagent delegation.",
        after="owner configuration explicitly refuses Codex native subagent delegation.",
        test_node=(
            "tests/test_codex_global_guidance.py::"
            "test_codex_global_guidance_preserves_owner_content_and_is_idempotent"
        ),
    ),
    DecisionMutation(
        mutation_id="native-only-product-host-inherits-agency-delegation-authority",
        invariant=(
            "Codex product delegation authority is injected only for Agency mode and is "
            "absent from native-only trials."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before=(
            "    base_options = (\n"
            "        CODEX_PRODUCT_EXEC_OPTIONS if agency_mode else "
            "_CODEX_NATIVE_ONLY_PRODUCT_EXEC_OPTIONS\n"
            "    )"
        ),
        after="    base_options = CODEX_PRODUCT_EXEC_OPTIONS",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_host_uses_isolated_workspace_write_profile"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-allows-store-bootstrap",
        invariant=(
            "Ordinary Codex product trials require the exact pre-existing Agency evidence store."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="        require_existing_store=True,",
        after="        require_existing_store=False,",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-drops-hook-start-evidence",
        invariant=("Agency-mode product trials capture content-free hook stage diagnostics."),
        source_path="agency_runtime/core/evals/product_host.py",
        before="        hook_event_diagnostics=master_enabled,",
        after="        hook_event_diagnostics=False,",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-disables-exact-rollout-correlation",
        invariant=(
            "Codex product trials correlate collaboration events from the exact child rollout."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="        require_exact_activation_rollout=True,",
        after="        require_exact_activation_rollout=False,",
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-restores-one-child-rollout-contract",
        invariant=(
            "Codex product trials project every exact product child instead of applying the "
            "one-child activation-canary topology."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before='        rollout_contract="product",',
        after='        rollout_contract="canary",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-host-notice-accepts-arbitrary-errors",
        invariant=(
            "Only exact known Codex non-critical host notices bypass the unexpected-item gate."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before="                if notice_type in CODEX_STDOUT_HOST_NOTICE_TYPES:\n",
        after='                if item_type == "error":\n',
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_jsonl_parser_classifies_only_exact_allowlisted_host_notices"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-product-drops-successful-child-patch-receipts",
        invariant=(
            "Codex product evidence preserves successful child patch receipts as bounded "
            "counts without retaining tool content."
        ),
        source_path="agency_runtime/core/codex_child_tool_evidence.py",
        before=('    "child_patch_apply_success_count",\n    "child_patch_apply_failure_count",\n'),
        after=(
            '    "child_patch_apply_success_count_removed",\n'
            '    "child_patch_apply_failure_count",\n'
        ),
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_product_child_tool_evidence_is_fixed_and_content_free"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-product-skips-nested-exec-tool-classification",
        invariant=(
            "Codex product evidence classifies allowlisted nested tools and the fixed "
            "wrapper outcome inside current functions.exec transport without retaining "
            "tool content."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before=('    nested = classify_codex_exec_nested_tools(payload.get("input"))\n'),
        after="    nested = None\n",
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_product_child_tool_evidence_is_fixed_and_content_free"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-product-collapses-wrapper-failure-category",
        invariant=(
            "Codex product evidence classifies failed exec wrappers into bounded fixed "
            "categories without retaining output content."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before=(
            "            failure = classify_codex_exec_wrapper_failure(exec_outputs.get(call_id))\n"
        ),
        after='            failure = "process_failed_other"\n',
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_product_child_tool_evidence_projects_fixed_wrapper_failure_category"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-product-collapses-wrapper-tool-outcome-correlation",
        invariant=(
            "Codex product evidence correlates each unambiguous nested tool kind with "
            "its wrapper outcome without retaining input or output content."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before=('        nested_kind = exec_nested_kinds.get(call_id, "ambiguous")\n'),
        after='        nested_kind = "ambiguous"\n',
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_product_child_tool_evidence_correlates_nested_tool_and_wrapper_outcome"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-execution-drops-parent-session-identity",
        invariant=(
            "Codex execution evidence requires the parent rollout to prove its exact "
            "session identity."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before=("        == 1\n    )\n\n\ndef _parent_followup_ciphertext_from_events("),
        after=("        >= 0\n    )\n\n\ndef _parent_followup_ciphertext_from_events("),
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_direct_completion_requires_exact_parent_and_causal_delivery"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-opaque-execution-drops-ciphertext-identity",
        invariant=(
            "Opaque Codex execution evidence requires one child ciphertext that is "
            "byte-identical to the exact parent follow-up ciphertext."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before=(
            "    return child_ciphertexts == [parent_ciphertext]\n\n\ndef _two_turn_boundaries("
        ),
        after=("    return len(child_ciphertexts) == 1\n\n\ndef _two_turn_boundaries("),
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_current_turn_matches_exact_parent_and_child_ciphertext"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-parent-stop-accepts-missing-child-final-response",
        invariant=(
            "A Codex worker closes only after its second turn contains one exact nonempty "
            "assistant final response."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before="    if response_index is None:\n        return False\n",
        after="    if False and response_index is None:\n        return False\n",
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_parent_stop_projection_requires_exact_completed_child_response"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-parent-stop-accepts-execution-after-child-response",
        invariant=(
            "The exact Codex execution delivery causally precedes the child final response."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before=(
            "        execution_event_start=boundaries[2] + 1,\n"
            "        execution_event_limit=response_index,\n"
        ),
        after=(
            "        execution_event_start=boundaries[2] + 1,\n"
            "        execution_event_limit=None,\n"
        ),
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_parent_stop_projection_rejects_tampered_or_ambiguous_completion"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-parent-stop-accepts-execution-before-second-turn",
        invariant=(
            "The exact Codex execution delivery occurs inside, not before, the second child turn."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before="        execution_event_start=boundaries[2] + 1,\n",
        after="        execution_event_start=None,\n",
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_parent_stop_projection_rejects_tampered_or_ambiguous_completion"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-direct-execution-drops-ciphertext-identity",
        invariant=(
            "Direct Codex execution requires a child NEW_TASK ciphertext byte-identical "
            "to the exact parent spawn ciphertext."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before=(
            "    return child_ciphertexts == [parent_ciphertext]\n\n\n"
            "def _current_turn_execution_observed_from_events("
        ),
        after=(
            "    return len(child_ciphertexts) == 1\n\n\n"
            "def _current_turn_execution_observed_from_events("
        ),
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_direct_initial_turn_requires_exact_spawn_ciphertext_and_completion"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-direct-completion-accepts-missing-final-response",
        invariant=(
            "Direct Codex completion requires one nonempty final response before task completion."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before=(
            "    response_index = _completed_initial_response_index(child_events, boundaries)\n"
            "    return bool(\n"
            "        response_index is not None\n"
        ),
        after=(
            "    response_index = _completed_initial_response_index(child_events, boundaries)\n"
            "    return bool(\n"
            "        True\n"
        ),
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_direct_completion_requires_exact_parent_and_causal_delivery"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-direct-completion-accepts-delivery-after-final-response",
        invariant=(
            "The exact direct Codex spawn delivery causally precedes the child final response."
        ),
        source_path="agency_runtime/core/codex_child_execution.py",
        before=(
            "            parent_events=parent_events,\n"
            "            execution_event_limit=response_index,\n"
        ),
        after=(
            "            parent_events=parent_events,\n            execution_event_limit=None,\n"
        ),
        test_node=(
            "tests/test_codex_child_execution.py::"
            "test_direct_completion_requires_exact_parent_and_causal_delivery"
        ),
    ),
    DecisionMutation(
        mutation_id="preflight-failure-drops-terminal-receipt",
        invariant=(
            "Every owned terminal preflight failure persists one exact content-free receipt."
        ),
        source_path="agency_runtime/core/preflight.py",
        before=(
            "                attempt_token=attempt_token,\n"
            '                status="preflight_failed",\n'
            "                failure_receipt=diagnostics.receipt(error),"
        ),
        after=(
            "                attempt_token=attempt_token,\n"
            '                status="preflight_failed",\n'
            "                failure_receipt=None,"
        ),
        test_node=(
            "tests/test_preflight_bounds.py::"
            "test_preflight_persists_request_kind_and_terminalizes_downstream_failure"
        ),
    ),
    DecisionMutation(
        mutation_id="preflight-failure-retains-raw-provider-content",
        invariant=(
            "Preflight failure receipts retain only allowlisted content-free provider attempts."
        ),
        source_path="agency_runtime/core/selector/receipt_projection.py",
        before='        return f"sha256:{digest}"',
        after="        return normalized",
        test_node=(
            "tests/test_preflight_bounds.py::"
            "test_preflight_failure_receipt_projects_provider_attempts_without_content"
        ),
    ),
    DecisionMutation(
        mutation_id="exact-snapshot-collapses-preflight-failure",
        invariant=(
            "Exact activation evidence projects one correlated preflight failure instead of "
            "collapsing it to route-not-found."
        ),
        source_path="agency_runtime/core/store/evidence.py",
        before="                    if route_count == 0",
        after="                    if False and route_count == 0",
        test_node=(
            "tests/test_canary_activation_snapshot.py::"
            "test_canary_activation_snapshot_projects_exact_preflight_failure"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-diagnostic-erases-parent-spawn-failure",
        invariant=(
            "A completed Codex turn with no native spawn reports that exact content-free cause."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before='    "parent_spawn_missing": "codex_parent_spawn_missing",',
        after=('    "parent_spawn_missing": "codex_collaboration_projection_unavailable",'),
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_v2_rollout_reports_content_free_parent_spawn_failure"
        ),
    ),
    DecisionMutation(
        mutation_id="product-trial-restores-canary-sized-deadline",
        invariant=(
            "A full product trial receives at least ten minutes for inference, all specialist "
            "units, validation, and final evidence."
        ),
        source_path="agency_runtime/core/evals/product_one_shot.py",
        before="MIN_PRODUCT_TRIAL_TIMEOUT_SECONDS: Final[float] = 600.0",
        after="MIN_PRODUCT_TRIAL_TIMEOUT_SECONDS: Final[float] = 1.0",
        test_node=(
            "tests/test_product_one_shot.py::"
            "test_product_trial_rejects_a_deadline_too_short_for_the_complete_contract"
        ),
    ),
    DecisionMutation(
        mutation_id="product-rollout-restores-stale-wait-ceiling",
        invariant=(
            "Product rollout evidence accepts the current bounded Codex wait contract without "
            "weakening the activation canary."
        ),
        source_path="agency_runtime/core/canary_backends.py",
        before="_CODEX_PRODUCT_MAX_WAIT_TIMEOUT_MS = 3_600_000",
        after="_CODEX_PRODUCT_MAX_WAIT_TIMEOUT_MS = 600_000",
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_product_rollout_projects_exact_eight_unit_reuse_topology"
        ),
    ),
    DecisionMutation(
        mutation_id="product-write-proof-assigns-read-only-child",
        invariant=("Only a delegated workspace-write child may create the product sentinel."),
        source_path="agency_runtime/core/evals/product_host.py",
        before=(
            '        "child with `mutation_scope=workspace_write` must check the relative file below "'
        ),
        after=(
            '        "child with `mutation_scope=read_only` must check the relative file below "'
        ),
        test_node=(
            "tests/test_product_host.py::"
            "test_workspace_write_proof_is_owned_by_a_delegated_workspace_write_unit"
        ),
    ),
    DecisionMutation(
        mutation_id="product-host-mislabels-hook-bypass-as-attended",
        invariant=(
            "Codex product trials record the supported one-invocation bypass without claiming "
            "attended trust."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before='        trust_mode="autonomous_bypass",',
        after='        trust_mode="attended",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_backend_persists_parent_and_correlates_exact_rollout"
        ),
    ),
    DecisionMutation(
        mutation_id="product-grading-accepts-missing-write-proof",
        invariant=(
            "Product grading fails closed unless effective workspace-write evidence is true."
        ),
        source_path="agency_runtime/core/evals/product_one_shot.py",
        before="        if execution.workspace_write_proven is not True",
        after="        if execution.workspace_write_proven is False",
        test_node=(
            "tests/test_product_one_shot.py::"
            "test_unproven_workspace_write_stops_before_product_grading[None]"
        ),
    ),
    DecisionMutation(
        mutation_id="default-fast-budget-removes-stage-repair",
        invariant=(
            "The default fast budget funds one bounded repair for both planner and recruiter."
        ),
        source_path="agency_runtime/core/config.py",
        before="    fast_call_budget: int = 4",
        after="    fast_call_budget: int = 3",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_default_fast_mode_funds_one_repair_for_each_inference_stage"
        ),
    ),
    DecisionMutation(
        mutation_id="declined-hiring-analysis-consumes-hire-budget",
        invariant=(
            "A declined hiring analysis does not consume the task's workforce-change "
            "allowance or starve a later declared gap."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before=(
            "        if not hireable or workforce_changes >= config.workforce.max_hires_per_turn:"
        ),
        # The eight-space indent is load-bearing: `before` is an indented
        # statement, so an unindented `after` yields an IndentationError, the
        # named test cannot be collected, and the mutation reports
        # `invalid_test_result` rather than killed or survived. It read as an
        # eval failure while proving nothing about the invariant.
        after=(
            "        if not hireable or len(attempted_units) >= "
            "config.workforce.max_hires_per_turn:"
        ),
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_route_hiring_caps_and_daily_budget_are_cumulative_and_truthful"
        ),
    ),
    DecisionMutation(
        mutation_id="causing-unit-binding-overflows-employment-schema",
        invariant="Causing-unit facts stay inside the employment contract item bound.",
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""        artifacts_produced=tuple(dict.fromkeys((unit.artifact_kind, *contract.artifacts_produced)))[
            :MAX_ITEMS
        ],""",
        after="""        artifacts_produced=tuple(dict.fromkeys((unit.artifact_kind, *contract.artifacts_produced)))[
            : MAX_ITEMS + 1
        ],""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_compiles_schema_maximum_lists_into_bounded_workforce_contract"
        ),
    ),
    DecisionMutation(
        mutation_id="workspace-hire-trusts-model-external-mutation",
        invariant=(
            "A workspace-local contractor receives the validated unit authority rather than "
            "a model-authored external-mutation claim."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before='        external_mutation=unit.mutation_scope == "external_write",',
        after="        external_mutation=contract.external_mutation,",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_workspace_unit_overrides_model_external_mutation_claim"
        ),
    ),
    DecisionMutation(
        mutation_id="external-write-hire-drops-approval-authority",
        invariant=(
            "An external-write work unit remains approval-gated even when the model "
            "understates mutation authority."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before='        external_mutation=unit.mutation_scope == "external_write",',
        after="        external_mutation=False,",
        # Re-anchored: the previous node asserted only hire status and never
        # inspected `external_mutation`, so this mutation survived the whole
        # hiring suite. The neighbouring `workspace_unit_overrides...` test
        # cannot kill it either -- it expects `False`, which is exactly what
        # hardcoding `external_mutation=False` produces. Only the understating
        # direction distinguishes them.
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_external_write_unit_overrides_an_understated_model_claim"
        ),
    ),
    DecisionMutation(
        mutation_id="explicit-risk-prohibition-becomes-granted-authority",
        invariant="An explicit high-risk prohibition does not grant the authority it denies.",
        source_path="agency_runtime/core/workforce/hiring_contract.py",
        before=(
            "        if _RISK_DENIAL_CLAUSE.match(clause) is None or "
            "_RISK_DENIAL_REVERSAL.match(clause):"
        ),
        after="        if marker in clause:",
        test_node=(
            "tests/test_workforce_hiring_contract.py::"
            "test_explicit_high_risk_prohibitions_do_not_grant_authority"
        ),
    ),
    DecisionMutation(
        mutation_id="positive-risk-after-prohibition-is-hidden",
        invariant=(
            "A later positive high-risk assertion cannot hide behind an earlier prohibition."
        ),
        source_path="agency_runtime/core/workforce/hiring_contract.py",
        before='_RISK_CLAUSE_SEPARATOR = re.compile(r"[.;!?]+|\\b(?:but|however)\\b")',
        after='_RISK_CLAUSE_SEPARATOR = re.compile(r"$^")',
        test_node=(
            "tests/test_workforce_hiring_contract.py::"
            "test_positive_risk_after_a_prohibition_still_requires_approval"
        ),
    ),
    DecisionMutation(
        mutation_id="owner-approval-gate-severed",
        invariant=(
            "An owner-gated high-risk contract never instantiates without recorded approval."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="    human_approval_required = compiled.human_approval_required",
        after="    human_approval_required = False",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_owner_gated_hire_waits_for_approval_then_materializes"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-outcomes-overflow-workforce-schema",
        invariant="Employment outcomes are capped to the smaller workforce projection.",
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""    outcomes = tuple(dict.fromkeys((*contract.capabilities, *contract.outcomes_owned)))[
        :MAX_OUTCOMES
    ]""",
        after="""    outcomes = tuple(dict.fromkeys((*contract.capabilities, *contract.outcomes_owned)))[
        :MAX_ITEMS
    ]""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_compiles_schema_maximum_lists_into_bounded_workforce_contract"
        ),
    ),
    DecisionMutation(
        mutation_id="amendment-target-identity-left-model-authored",
        invariant=(
            "An amendment revises the inference-selected existing worker instead of creating a "
            "second model-authored identity."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="    contract = replace(contract, slug=existing.agent_id)",
        after="    contract = contract",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_amendment_binds_model_extension_slug_to_inferred_target"
        ),
    ),
    DecisionMutation(
        mutation_id="task-gap-restores-near-match-amendment",
        invariant=(
            "An ordinary task gap creates a distinct exact specialist instead of broadening "
            "a near-match."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before=(
            '    if action == "amend" and not allow_existing_worker_amendment:\n'
            '        raise _CandidateValidationFailure("task_gap_requires_distinct_specialist")'
        ),
        after=(
            '    if False and action == "amend" and not allow_existing_worker_amendment:\n'
            '        raise _CandidateValidationFailure("task_gap_requires_distinct_specialist")'
        ),
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_task_gap_amendment_is_rejected_when_amendment_is_disallowed"
        ),
    ),
    DecisionMutation(
        mutation_id="amendment-outcomes-overflow-workforce-schema",
        invariant=(
            "An additive amendment preserves existing outcomes while respecting the smaller "
            "workforce projection bound."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""    agent["outcomes"] = _bounded_additive(
        existing.outcomes,
        agent["outcomes"],
        maximum=MAX_OUTCOMES,
    )""",
        after="""    agent["outcomes"] = list(
        dict.fromkeys((*existing.outcomes, *agent["outcomes"]))
    )""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_amendment_preserves_existing_values_inside_smaller_workforce_bounds"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-diagnostics-collapse",
        invariant="Post-parse contractor failures retain their content-free validation stage.",
        source_path="agency_runtime/core/workforce/hiring.py",
        # Anchored through the `_candidate_documents` call so it names the
        # POST-PARSE failure specifically: the pre-contract evidence gate now
        # reports through the same exception, so a bare one-line anchor matches
        # twice and silently stops identifying a unique mutation site.
        before=(
            "            store=store,\n"
            "        )\n"
            "    except _CandidateValidationFailure as exc:\n"
            "        return failure(exc.reason_code)"
        ),
        after=(
            "            store=store,\n"
            "        )\n"
            "    except _CandidateValidationFailure as exc:\n"
            '        return failure("contract_invalid:candidate")'
        ),
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_reports_content_free_employment_revalidation_stage"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-critic-loses-typed-gap-projection",
        invariant=(
            "A contractor critic receives bounded typed requirements and eligible coverage "
            "from the exact staffing-verifier context."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="""        "verified_gap": _verified_gap_projection(
            unit,
            contracts,
            reason_codes=verified_gap_reasons,
            staffing_context=staffing_context,
        ),""",
        after="""        "verified_gap": {
            "inference_declared": "inference_declared_gap" in verified_gap_reasons,
            "reason_codes": list(verified_gap_reasons),
        },""",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_critic_can_independently_validate_runtime_gap_evidence"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-repair-keeps-incoherent-relationships",
        invariant=(
            "A replacement contractor is explicitly told to remove speculative composition "
            "edges after a relationship-coherence rejection."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="relationship-coherence codes, remove speculative",
        after="relationship-coherence codes, retain speculative",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_product_request_gap_repair_receives_live_reason_family_and_typed_proof"
        ),
    ),
    DecisionMutation(
        mutation_id="contractor-repair-ignores-acceptance-evidence",
        invariant=(
            "A replacement contractor binds its evidence and evaluations to every work-unit "
            "acceptance check after an evidence-sufficiency rejection."
        ),
        source_path="agency_runtime/core/workforce/hiring.py",
        before="codes, bind evidence requirements and evaluations",
        after="codes, ignore evidence requirements and evaluations",
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_product_request_gap_repair_receives_live_reason_family_and_typed_proof"
        ),
    ),
    DecisionMutation(
        mutation_id="terminal-inference-failure-restores-policy-selection",
        invariant=(
            "A terminal inference failure cannot be repopulated by deterministic policy "
            "companions or fallbacks."
        ),
        source_path="agency_runtime/core/selector/pipeline.py",
        before=(
            '    inference_failed = semantic_status in {"inference_unavailable", '
            '"inference_invalid"}'
        ),
        after="    inference_failed = False",
        test_node=(
            "tests/test_routing_correctness.py::"
            "test_full_route_never_repopulates_inference_failure_from_policy"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-terminal-invalid-restores-continuation-prompt",
        invariant=(
            "A terminal Codex response failure stops the turn instead of creating a "
            "model-visible correction prompt."
        ),
        source_path="agency_runtime/adapters/hooks.py",
        before="        return self._reject_completion(message, retry=True)",
        after="        return self._reject_completion(message, retry=False)",
        test_node=(
            "tests/test_host_hooks.py::"
            "test_identical_codex_invalid_stop_is_terminal_and_exactly_replayed"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-preflight-drops-initial-header-snapshot",
        invariant=(
            "Codex receives the exact Store-backed header snapshot before its first visible "
            "response."
        ),
        source_path="agency_runtime/adapters/hooks.py",
        before='            marker="INITIAL",',
        after='            marker="REMOVED",',
        test_node=(
            "tests/test_host_hooks.py::test_codex_stdio_preflight_header_is_accepted_first_pass"
        ),
    ),
    DecisionMutation(
        mutation_id="openclaw-finalize-restores-model-revision",
        invariant=(
            "OpenClaw terminal verification never asks the model to revise a natural response."
        ),
        source_path="agency_runtime/core/installer_payload_openclaw.py",
        before="""      if (decision?.terminalRejected === true) {{
        rememberTerminalRejection(decision, event, ctx);
        return undefined;
      }}""",
        after="""      if (decision?.terminalRejected === true) {{
        rememberTerminalRejection(decision, event, ctx);
        return {{ action: "revise", message: String(decision?.message || "") }};
      }}""",
        test_node=(
            "tests/test_adapter_parity.py::"
            "test_generated_openclaw_plugin_is_native_openclaw_package"
        ),
    ),
    DecisionMutation(
        mutation_id="hermes-transform-repairs-unfinalized-response",
        invariant=(
            "Hermes blocks an unfinalized natural response instead of repairing it after "
            "generation."
        ),
        source_path="agency_runtime/adapters/hermes/bridge.py",
        before='        if decision.get("action") != "accept":',
        after='        if False and decision.get("action") != "accept":',
        test_node=(
            "tests/test_completion_policy_boundary.py::"
            "test_hermes_transform_rejects_unfinalized_natural_response_without_repair"
        ),
    ),
    DecisionMutation(
        mutation_id="ranking-order-reversed",
        invariant="The model's semantic ranking order is preserved, never locally reranked.",
        source_path="agency_runtime/core/workforce/inference.py",
        before="    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))",
        after="    ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]))",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_inference_uses_semantic_order_without_trusting_uncalibrated_score_gaps"
        ),
    ),
)

PytestRunner = Callable[[Path, Sequence[str], str, float, Path], _PytestRun]


def _normalized_node(value: str) -> str:
    return value.strip().replace(chr(92), "/")


def _failed_nodes(output: str) -> tuple[str, ...]:
    nodes: list[str] = []
    for line in output.splitlines():
        if not line.startswith("FAILED "):
            continue
        node = _normalized_node(line.removeprefix("FAILED ").split(" - ", 1)[0])
        if node and node not in nodes:
            nodes.append(node)
    return tuple(nodes)


def _run_pytest(
    checkout: Path,
    test_nodes: Sequence[str],
    python_executable: str,
    timeout_seconds: float,
    source_root: Path,
) -> _PytestRun:
    scratch = checkout / ".decision-conformance"
    scratch.mkdir(parents=True, exist_ok=True)
    home = scratch / "home"
    temporary = scratch / "temp"
    bytecode = scratch / "bytecode"
    for directory in (home, temporary, bytecode):
        directory.mkdir(parents=True, exist_ok=True)
    environment = least_privilege_subprocess_environment(
        "decision-conformance",
        home_dir=home,
        current_directory=checkout,
        forbidden_roots=(source_root,),
        extra_env={
            "AGENCY_CI_PYTHON": python_executable,
            "AGENCY_DECISION_CONFORMANCE": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(checkout),
            "PYTHONPYCACHEPREFIX": str(bytecode),
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
        },
    )
    command = [
        python_executable,
        "-m",
        "pytest",
        *test_nodes,
        "-q",
        "-W",
        "error",
        "--maxfail=1",
        "-p",
        "no:cacheprovider",
        f"--basetemp={temporary / 'pytest'}",
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=checkout,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _PytestRun(
            exit_code=None,
            failed_nodes=(),
            duration_ms=round((time.perf_counter() - started) * 1000),
            timed_out=True,
        )
    output = completed.stdout + chr(10) + completed.stderr
    return _PytestRun(
        exit_code=completed.returncode,
        failed_nodes=_failed_nodes(output),
        duration_ms=round((time.perf_counter() - started) * 1000),
        failure_excerpt=(output[-4096:] if completed.returncode else None),
    )


def _run_baseline(
    checkout: Path,
    test_nodes: Sequence[str],
    python_executable: str,
    timeout_seconds: float,
    source_root: Path,
    *,
    pytest_runner: PytestRunner,
) -> _PytestRun:
    """Run each baseline node under the documented per-test deadline."""

    duration_ms = 0
    for test_node in test_nodes:
        result = pytest_runner(
            checkout,
            (test_node,),
            python_executable,
            timeout_seconds,
            source_root,
        )
        duration_ms += result.duration_ms
        if result.timed_out or result.exit_code != 0:
            return _PytestRun(
                exit_code=result.exit_code,
                failed_nodes=result.failed_nodes,
                duration_ms=duration_ms,
                timed_out=result.timed_out,
                failure_excerpt=result.failure_excerpt,
            )
    return _PytestRun(exit_code=0, failed_nodes=(), duration_ms=duration_ms)


def _relative_file(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if not candidate.parts or candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("decision-conformance paths must stay repository-relative")
    current = root
    try:
        for index, part in enumerate(candidate.parts):
            current /= part
            metadata = os.lstat(current)
            if metadata_is_link_or_reparse_point(metadata):
                raise ValueError(
                    "decision-conformance inputs must not cross a link or reparse point"
                )
            if index < len(candidate.parts) - 1 and not stat.S_ISDIR(metadata.st_mode):
                raise ValueError("decision-conformance input parent must be a directory")
        resolved = current.resolve(strict=True)
    except OSError as exc:
        raise ValueError("decision-conformance input is unavailable") from exc
    try:
        resolved.relative_to(root)
    except ValueError:
        raise ValueError("decision-conformance path escapes the repository") from None
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("decision-conformance inputs must be regular files")
    return resolved


def _regular_tree_files(root: Path) -> tuple[Path, ...]:
    """Inventory a real, link-free source tree before it is copied."""

    try:
        root_metadata = os.lstat(root)
    except OSError as exc:
        raise ValueError("decision-conformance source tree is unavailable") from exc
    if metadata_is_link_or_reparse_point(root_metadata) or not stat.S_ISDIR(root_metadata.st_mode):
        raise ValueError("decision-conformance source tree must be a real directory")
    files: list[Path] = []
    for current, directory_names, file_names in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        directory_names.sort()
        file_names.sort()
        current_path = Path(current)
        for name in directory_names:
            candidate = current_path / name
            try:
                metadata = os.lstat(candidate)
            except OSError as exc:
                raise ValueError("decision-conformance source tree changed") from exc
            if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
                raise ValueError(
                    "decision-conformance source tree contains a link or reparse point"
                )
        for name in file_names:
            candidate = current_path / name
            try:
                metadata = os.lstat(candidate)
            except OSError as exc:
                raise ValueError("decision-conformance source tree changed") from exc
            if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISREG(metadata.st_mode):
                raise ValueError(
                    "decision-conformance source tree contains a link or "
                    "reparse point or a non-regular file"
                )
            files.append(candidate)
    return tuple(files)


def _validate_repository(root: Path, mutations: Sequence[DecisionMutation]) -> Path:
    try:
        resolved = root.expanduser().resolve(strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ValueError("decision-conformance repository is unavailable") from exc
    if not resolved.is_dir() or not (resolved / "pyproject.toml").is_file():
        raise ValueError("decision-conformance requires an Agency Runtime repository root")
    if not (resolved / "agency_runtime").is_dir() or not (resolved / "tests").is_dir():
        raise ValueError("decision-conformance repository inputs are incomplete")
    seen_ids: set[str] = set()
    for mutation in mutations:
        if not mutation.mutation_id or mutation.mutation_id in seen_ids:
            raise ValueError("decision-conformance mutation ids must be unique")
        seen_ids.add(mutation.mutation_id)
        _relative_file(resolved, mutation.source_path)
        test_path = mutation.test_node.split("::", 1)[0]
        if not test_path.startswith("tests/") or "::" not in mutation.test_node:
            raise ValueError("decision-conformance test nodes must name one test")
        _relative_file(resolved, test_path)
        if not mutation.before or mutation.before == mutation.after:
            raise ValueError("decision-conformance mutations require a real exact replacement")
    return resolved


def _copy_inputs(
    source_root: Path,
    destination: Path,
    mutations: Sequence[DecisionMutation],
) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source_root / "pyproject.toml", destination / "pyproject.toml")
    _regular_tree_files(source_root / "agency_runtime")
    shutil.copytree(
        source_root / "agency_runtime",
        destination / "agency_runtime",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
    )
    _regular_tree_files(destination / "agency_runtime")
    destination_tests = destination / "tests"
    destination_tests.mkdir()
    relative_tests = {mutation.test_node.split("::", 1)[0] for mutation in mutations}
    relative_tests.update(
        f"tests/{name}" for name in _COPY_SUPPORT if (source_root / "tests" / name).is_file()
    )
    for relative in sorted(relative_tests):
        source = _relative_file(source_root, relative)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def _fingerprints(
    root: Path,
    mutations: Sequence[DecisionMutation],
) -> dict[str, str]:
    relative_files = {"pyproject.toml"}
    for source in _regular_tree_files(root / "agency_runtime"):
        if "__pycache__" not in source.parts and source.suffix not in {".pyc", ".pyo"}:
            relative_files.add(source.relative_to(root).as_posix())
    relative_files.update(mutation.test_node.split("::", 1)[0] for mutation in mutations)
    relative_files.update(
        f"tests/{name}" for name in _COPY_SUPPORT if (root / "tests" / name).is_file()
    )
    return {
        relative: hashlib.sha256(_relative_file(root, relative).read_bytes()).hexdigest()
        for relative in sorted(relative_files)
    }


def _mutation_result(
    mutation: DecisionMutation,
    checkout: Path,
    *,
    python_executable: str,
    timeout_seconds: float,
    source_root: Path,
    pytest_runner: PytestRunner,
) -> dict[str, Any]:
    target = _relative_file(checkout, mutation.source_path)
    text = target.read_text(encoding="utf-8")
    occurrences = text.count(mutation.before)
    if occurrences != 1:
        return {
            "mutation_id": mutation.mutation_id,
            "invariant": mutation.invariant,
            "source_path": mutation.source_path,
            "test_node": mutation.test_node,
            "status": "stale_anchor",
            "anchor_occurrences": occurrences,
            "exit_code": None,
            "failed_nodes": [],
            "duration_ms": 0,
        }
    target.write_text(text.replace(mutation.before, mutation.after, 1), encoding="utf-8")
    result = pytest_runner(
        checkout,
        (mutation.test_node,),
        python_executable,
        timeout_seconds,
        source_root,
    )
    expected = _normalized_node(mutation.test_node)
    failed = tuple(_normalized_node(node) for node in result.failed_nodes)
    expected_failed = len(failed) == 1 and (
        failed[0] == expected or failed[0].startswith(expected + "[")
    )
    if result.timed_out:
        status = "timeout"
    elif result.exit_code == 0:
        status = "survived"
    elif result.exit_code == 1 and expected_failed:
        status = "killed"
    else:
        status = "invalid_test_result"
    return {
        "mutation_id": mutation.mutation_id,
        "invariant": mutation.invariant,
        "source_path": mutation.source_path,
        "test_node": mutation.test_node,
        "status": status,
        "anchor_occurrences": occurrences,
        "exit_code": result.exit_code,
        "failed_nodes": list(failed),
        "duration_ms": result.duration_ms,
    }


def run_decision_conformance_eval(
    repository: str | Path = ".",
    *,
    mutations: Sequence[DecisionMutation] = MUTATIONS,
    python_executable: str | None = None,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    pytest_runner: PytestRunner = _run_pytest,
) -> dict[str, Any]:
    """Prove a green baseline and kill every curated mutation in private copies."""

    if not mutations:
        raise ValueError("decision-conformance requires at least one mutation")
    if not 1.0 <= float(timeout_seconds) <= 300.0:
        raise ValueError("decision-conformance timeout must be from 1 through 300 seconds")
    source_root = _validate_repository(Path(repository), mutations)
    interpreter = str(Path(python_executable or sys.executable).resolve(strict=True))
    before = _fingerprints(source_root, mutations)
    baseline_nodes = tuple(dict.fromkeys(mutation.test_node for mutation in mutations))
    mutation_results: list[dict[str, Any]] = []

    with private_temporary_directory(prefix="decision-conformance") as temporary:
        baseline_copy = temporary / "baseline"
        _copy_inputs(source_root, baseline_copy, mutations)
        baseline_run = _run_baseline(
            baseline_copy,
            baseline_nodes,
            interpreter,
            float(timeout_seconds),
            source_root,
            pytest_runner=pytest_runner,
        )
        baseline_passed = baseline_run.exit_code == 0 and not baseline_run.timed_out
        if baseline_passed:
            for index, mutation in enumerate(mutations):
                mutation_copy = temporary / f"mutation-{index:02d}"
                _copy_inputs(source_root, mutation_copy, mutations)
                mutation_results.append(
                    _mutation_result(
                        mutation,
                        mutation_copy,
                        python_executable=interpreter,
                        timeout_seconds=float(timeout_seconds),
                        source_root=source_root,
                        pytest_runner=pytest_runner,
                    )
                )

    after = _fingerprints(source_root, mutations)
    source_unchanged = before == after
    killed = sum(item["status"] == "killed" for item in mutation_results)
    passed = (
        baseline_passed
        and source_unchanged
        and len(mutation_results) == len(mutations)
        and killed == len(mutations)
    )
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "passed": passed,
        "status": "passed" if passed else "failed",
        "repository": str(source_root),
        "source_unchanged": source_unchanged,
        "source_scope": ("pyproject.toml, agency_runtime regular files, and selected test inputs"),
        "baseline": {
            "status": (
                "timeout"
                if baseline_run.timed_out
                else "passed"
                if baseline_run.exit_code == 0
                else "failed"
            ),
            "exit_code": baseline_run.exit_code,
            "failed_nodes": list(baseline_run.failed_nodes),
            "failure_excerpt": baseline_run.failure_excerpt,
            "test_nodes": list(baseline_nodes),
            "duration_ms": baseline_run.duration_ms,
        },
        "counts": {
            "mutations": len(mutations),
            "killed": killed,
            "survived": sum(item["status"] == "survived" for item in mutation_results),
            "invalid": sum(
                item["status"] not in {"killed", "survived"} for item in mutation_results
            ),
        },
        "mutations": mutation_results,
        "evidence_boundary": (
            "Curated decision sensitivity only; no coverage, superiority, "
            "or exhaustive mutation claim."
        ),
    }


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "MUTATIONS",
    "SCHEMA",
    "VERSION",
    "DecisionMutation",
    "run_decision_conformance_eval",
]
