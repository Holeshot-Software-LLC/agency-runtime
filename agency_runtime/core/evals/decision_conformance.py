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
            "executed prompt hash."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before="""        if normalized_host == "codex" and normalized_mode == "agency":
            evidence = store.get_canary_activation_snapshot(
                host=normalized_host,
                query_hash=executed_prompt_hash.removeprefix("sha256:"),
            )""",
        after="""        if normalized_host == "codex" and normalized_mode == "agency":
            evidence = store.recent_runtime_activity(limit=500)""",
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
        mutation_id="isolated-plan-repeats-full-request-per-unit",
        invariant=(
            "A bounded isolated delegation plan encodes one shared request prefix rather than "
            "repeating the complete request in every specialist row."
        ),
        source_path="agency_runtime/core/preflight_recipe.py",
        before=(
            "    if len(prefix) < 128 or any(\n"
            "        not goal.startswith(prefix) or len(goal) == len(prefix) for goal in goals\n"
            "    ):\n"
            '        return ""\n'
            "    return prefix"
        ),
        after=(
            "    if len(prefix) < 128 or any(\n"
            "        not goal.startswith(prefix) or len(goal) == len(prefix) for goal in goals\n"
            "    ):\n"
            '        return ""\n'
            '    return ""'
        ),
        test_node=(
            "tests/test_unit_aware_delegation.py::"
            "test_isolated_multi_unit_context_encodes_one_shared_request_prefix"
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
        test_node=(
            "tests/test_unit_aware_delegation.py::"
            "test_isolated_multi_unit_context_encodes_one_shared_request_prefix"
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
        mutation_id="legacy-preflight-replay-uses-current-goal-renderer",
        invariant=(
            "A stored legacy recipe reconstructs the exact full-goal rendering governed by "
            "its recorded context-policy version."
        ),
        source_path="agency_runtime/core/preflight_recipe.py",
        before=(
            "    shared_goal_prefix = (\n"
            "        _shared_delegation_goal_prefix(goals) "
            'if int(context_policy_version) >= 12 else ""\n'
            "    )"
        ),
        after="    shared_goal_prefix = _shared_delegation_goal_prefix(goals)",
        test_node=(
            "tests/test_unit_aware_delegation.py::"
            "test_v11_isolated_context_preserves_full_goal_rows"
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
        mutation_id="activation-replay-drops-inferred-binding",
        invariant=(
            "The content-free activation recipe retains the exact inferred unit binding needed "
            "for modern plan replay."
        ),
        source_path="agency_runtime/core/store/preflight.py",
        before=(
            '    activation_canary = str(value.get("source") or "") == '
            "CODEX_ACTIVATION_CANARY_ROUTE_SOURCE"
        ),
        after="    activation_canary = False",
        test_node=(
            "tests/test_activation_canary_contract.py::"
            "test_activation_canary_preflight_replays_one_exact_selected_only_unit"
        ),
    ),
    DecisionMutation(
        mutation_id="modern-preflight-plan-drift-is-accepted",
        invariant="Modern durable unit plans must exactly match their replayed construction.",
        source_path="agency_runtime/core/preflight_recipe.py",
        before="    elif rebuilt != unit_agent_plan:",
        after="    elif False:",
        test_node=(
            "tests/test_turn_coverage_complete_header_preflight.py::"
            "test_preflight_recipe_rejects_current_unit_plan_drift"
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
            "Codex product trials give the parent explicit authority to dispatch every "
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
        mutation_id="product-host-restores-code-reviewer-canary-proof",
        invariant=(
            "Codex product trials grade the complete inferred unit plan rather than the "
            "one-unit code-reviewer activation canary."
        ),
        source_path="agency_runtime/core/evals/product_host.py",
        before='            activation_contract="product",',
        after='            activation_contract="canary",',
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_host_uses_unmocked_multi_unit_product_proof"
        ),
    ),
    DecisionMutation(
        mutation_id="product-guidance-restores-parent-plan-refinement",
        invariant=(
            "The parent dispatches every inferred product unit exactly once instead of "
            "merging, omitting, or performing specialist units itself."
        ),
        source_path="agency_runtime/core/host_guidance.py",
        before=(
            '        f"{dispatch} Dispatch every persisted plan row exactly once; do not merge, omit, "'
        ),
        after=('        f"{dispatch} The host may refine, merge, or decline the suggested rows; "'),
        test_node=(
            "tests/test_delegation_operational_projection.py::"
            "test_native_delegation_guidance_requires_every_exact_plan_row"
        ),
    ),
    DecisionMutation(
        mutation_id="product-proof-allows-parent-product-tools",
        invariant=(
            "The product parent coordinates exact children but never performs product work "
            "through its own non-collaboration tools."
        ),
        source_path="agency_runtime/core/canary_proof.py",
        before='    if counts["unexpected_item_count"] != 0:',
        after='    if False and counts["unexpected_item_count"] != 0:',
        test_node=(
            "tests/test_product_host.py::"
            "test_product_proof_rejects_parent_side_product_tool_execution"
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
        mutation_id="product-proof-drops-host-notice-projection",
        invariant=(
            "Product proof preserves the same validated content-free Codex host notice "
            "types and count observed by the backend."
        ),
        source_path="agency_runtime/core/canary_proof.py",
        before=(
            '        "host_notice_types": list(host_notice_types),\n'
            '        "evidence_source": "persisted_rollout",\n'
        ),
        after=(
            '        "host_notice_types": [],\n        "evidence_source": "persisted_rollout",\n'
        ),
        test_node=(
            "tests/test_product_host.py::"
            "test_codex_product_host_uses_unmocked_multi_unit_product_proof"
        ),
    ),
    DecisionMutation(
        mutation_id="product-proof-allows-invalid-host-notice-projection",
        invariant=(
            "Malformed or missing Codex host-notice evidence cannot produce a passing "
            "product proof."
        ),
        source_path="agency_runtime/core/canary_proof.py",
        before="        and collaboration_projection is None\n",
        after="        and False\n",
        test_node=(
            "tests/test_product_host.py::"
            "test_product_collaboration_projection_rejects_invalid_host_notice_evidence"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-opaque-child-restores-canary-only-delivery",
        invariant=(
            "Any exact persisted Codex product row can receive its specialist context; "
            "opaque delivery is not restricted to the fixed activation canary."
        ),
        source_path="agency_runtime/adapters/hooks.py",
        before=(
            "                    if assignment is None or pending_identity != "
            "assignment_identity:\n"
            '                        raise ValueError("pending Codex delivery does not '
            'match the exact plan")\n'
            "                    exact_delivery = "
            "render_codex_opaque_native_child_prompt_delivery("
        ),
        after=(
            "                    if assignment is None or pending_identity != "
            "assignment_identity:\n"
            '                        raise ValueError("pending Codex delivery does not '
            'match the exact plan")\n'
            "                    from agency_runtime.core.activation_canary_contract import (\n"
            "                        CODEX_ACTIVATION_CANARY_WORK_UNIT,\n"
            "                    )\n"
            "                    if assignment.goal_hash != work_unit_goal_hash(\n"
            "                        CODEX_ACTIVATION_CANARY_WORK_UNIT\n"
            "                    ):\n"
            '                        raise ValueError("pending Codex delivery is not the '
            'activation canary")\n'
            "                    exact_delivery = "
            "render_codex_opaque_native_child_prompt_delivery("
        ),
        test_node=(
            "tests/test_claude_native_child_hooks.py::"
            "test_codex_opaque_product_delivery_is_goal_hash_bound_child_context"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-opaque-child-drops-goal-hash-binding",
        invariant=("Opaque Codex child context carries the exact persisted work-unit goal hash."),
        source_path="agency_runtime/adapters/hooks.py",
        before=(
            "                    exact_delivery = "
            "render_codex_opaque_native_child_prompt_delivery(\n"
            '                        str(pending.get("prompt_body") or ""),\n'
            "                        parent_session_id=session_id,\n"
            "                        parent_trace_id=trace_id,\n"
            "                        tool_use_id=assignment.tool_use_id,\n"
            "                        work_unit_id=assignment.work_unit_id,\n"
            "                        specialist_slug=assignment.specialist_slug,\n"
            "                        specialist_version=assignment.specialist_version,\n"
            "                        specialist_prompt_hash=assignment.specialist_prompt_hash,\n"
            "                        goal_hash=assignment.goal_hash,\n"
            "                    )"
        ),
        after=(
            "                    exact_delivery = "
            "render_codex_opaque_native_child_prompt_delivery(\n"
            '                        str(pending.get("prompt_body") or ""),\n'
            "                        parent_session_id=session_id,\n"
            "                        parent_trace_id=trace_id,\n"
            "                        tool_use_id=assignment.tool_use_id,\n"
            "                        work_unit_id=assignment.work_unit_id,\n"
            "                        specialist_slug=assignment.specialist_slug,\n"
            "                        specialist_version=assignment.specialist_version,\n"
            "                        specialist_prompt_hash=assignment.specialist_prompt_hash,\n"
            '                        goal_hash="0" * 64,\n'
            "                    )"
        ),
        test_node=(
            "tests/test_claude_native_child_hooks.py::"
            "test_codex_opaque_product_delivery_is_goal_hash_bound_child_context"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-opaque-child-restores-workspace-wide-grant",
        invariant=(
            "An ordinary Codex child receives only the path prefixes derived from its "
            "exact preflight work unit, never an unconditional repository-wide grant."
        ),
        source_path="agency_runtime/core/unit_assignment.py",
        before=(
            "    path_prefixes = (\n"
            "        []\n"
            '        if normalized_scope == "read_only"\n'
            '        else ["." if resource == "repository-workspace" else resource '
            "for resource in resources]\n"
            "    )"
        ),
        after=(
            "    path_prefixes = (\n"
            "        []\n"
            '        if normalized_scope == "read_only"\n'
            '        else ["."]\n'
            "    )"
        ),
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_preflight_stages_exact_path_for_ordinary_workspace_write"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-path-authority-restores-case-folding",
        invariant=(
            "Canonical mutation paths preserve case; a separate folded key owns only "
            "conservative contention matching."
        ),
        source_path="agency_runtime/core/unit_assignment.py",
        before="    return normalized[:MAX_RESOURCE_CHARS]\n",
        after="    return normalized.casefold()[:MAX_RESOURCE_CHARS]\n",
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_preflight_stages_exact_path_for_ordinary_workspace_write"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-opaque-child-restores-concurrent-unconsumed-grants",
        invariant=(
            "Codex opaque launches remain serialized until SubagentStart consumes the "
            "prior native-hook grant."
        ),
        source_path="agency_runtime/core/store/delegation_activation.py",
        before="    if inflight is not None:\n",
        after="    if False and inflight is not None:\n",
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_opaque_children_serialize_until_subagent_start_consumes_grant"
        ),
    ),
    DecisionMutation(
        mutation_id="codex-plaintext-child-inherits-opaque-serialization",
        invariant=(
            "Only token-free opaque Codex grants serialize through child start; "
            "plaintext token-correlated grants may coexist."
        ),
        source_path="agency_runtime/core/store/delegation_activation.py",
        before="    if planned_scope is None or not opaque_launch:\n",
        after="    if planned_scope is None:\n",
        test_node=(
            "tests/test_codex_activation_canary.py::"
            "test_codex_plaintext_grants_skip_the_opaque_serialization_slot"
        ),
    ),
    DecisionMutation(
        mutation_id="preflight-failure-drops-terminal-receipt",
        invariant=(
            "Every owned terminal preflight failure persists one exact content-free receipt."
        ),
        source_path="agency_runtime/core/preflight.py",
        before=(
            "                    attempt_token=attempt_token,\n"
            '                    status="preflight_failed",\n'
            "                    failure_receipt=diagnostics.receipt(error),"
        ),
        after=(
            "                    attempt_token=attempt_token,\n"
            '                    status="preflight_failed",\n'
            "                    failure_receipt=None,"
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
        mutation_id="codex-delegation-inherits-parent-history",
        invariant=(
            "Codex specialist launches exclude parent history while receiving the exact "
            "hook-injected specialist context."
        ),
        source_path="agency_runtime/core/specialist_context.py",
        before=('                "set `fork_turns` to `none` and set `task_name` to that row\'s "'),
        after='                "set `task_name` to that row\'s "',
        test_node=(
            "tests/test_unit_aware_delegation.py::"
            "test_isolated_native_hook_receives_exact_unit_agent_plan[codex]"
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
        mutation_id="default-fast-budget-removes-recruiter-repair",
        invariant=(
            "The default fast budget funds planning, recruitment, and one bounded semantic repair."
        ),
        source_path="agency_runtime/core/config.py",
        before="    fast_call_budget: int = 3",
        after="    fast_call_budget: int = 2",
        test_node=(
            "tests/test_workforce_inference.py::"
            "test_default_fast_mode_funds_recruiter_contract_repair_after_planning"
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
            "        if not hireable or workforce_changes >= config.workforce.max_hires_per_task:"
        ),
        after=(
            "        if not hireable or len(attempted_units) >= "
            "config.workforce.max_hires_per_task:"
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
            '        return failure("task_gap_requires_distinct_specialist")'
        ),
        after=(
            '    if False and action == "amend" and not allow_existing_worker_amendment:\n'
            '        return failure("task_gap_requires_distinct_specialist")'
        ),
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_task_gap_rejects_near_match_amendment_in_open_ended_pool"
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
        before="        return failure(exc.reason_code)",
        after='        return failure("contract_invalid:candidate")',
        test_node=(
            "tests/test_workforce_dynamic_hiring.py::"
            "test_hire_reports_content_free_employment_revalidation_stage"
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
        mutation_id="isolated-plan-normalization-bypasses-specialist-gate",
        invariant=(
            "An isolated route rejected for lacking a child-activation plan cannot reach the "
            "parent as an accepted substantive turn."
        ),
        source_path="agency_runtime/core/preflight.py",
        before=(
            "        _require_substantive_specialist(routing, classification, diagnostics)\n"
            "        if diagnostics is not None:\n"
            '            diagnostics.enter("context_hydration")\n'
            '        if delivery_mode == "isolated":'
        ),
        after=(
            "        if diagnostics is not None:\n"
            '            diagnostics.enter("context_hydration")\n'
            '        if delivery_mode == "isolated":'
        ),
        test_node=(
            "tests/test_preflight_bounds.py::"
            "test_isolated_preflight_blocks_selection_without_an_activation_plan"
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
