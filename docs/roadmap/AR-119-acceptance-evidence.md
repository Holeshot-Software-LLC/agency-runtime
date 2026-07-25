---
title: "AR-119 acceptance evidence summary"
status: active
category: roadmap
created: 2026-07-24
updated: 2026-07-24
tags: [roadmap, acceptance, evidence, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
supersedes: []
superseded_by: null
type: roadmap
---

# AR-119 acceptance evidence

This maps each child issue's acceptance criteria to concrete evidence
produced during the ADR-0087 implementation on PR #140 (merged) and the
child-routing follow-up.

## AR-120: Normalize and audit the complete workforce recruitment index

- [x] **Every governed worker has a complete normalized recruitment contract.**
  All 263 bundled specialists project through `project_workforce_contract`
  with versioned `schema_version`, `worker_id`, `capability_ids`, and
  audited `audit` provenance. Verified: `workforce_index_snapshot` over
  the full roster returns 263 contracts with zero nulls.
- [x] **Typed relationships replace overloaded conflict semantics.**
  `CompositionContract.same_context_conflicts`, `selection_exclusive`,
  `requires`, `must_follow`, `complements`, `substitution_group`, and
  `independence_class` replace the legacy `conflicts_with` string list.
  `workforce_index_fingerprint` validates the closure.
- [x] **Every projection is independently checked against its prompt body.**
  `_content_hash` enforces exact SHA-256 for `version_hash`; D1 (commit
  `8b95ab0`) reconciled opaque roster hashes with the governed contract
  digest. `content_identity_matches` tolerates opaque upstream tokens.
- [ ] **Nightly ingestion updates contracts, confusion groups, and evaluations safely.**
  The `roster-upstream-audit.yml` workflow runs nightly but has not been
  validated against a live upstream delta in this cycle.

## AR-121: Inference-first planning and deterministic staffing

- [x] **Configured inference plans before recruiting and sees the whole workforce.**
  `plan_and_staff_workforce` (commit `70c28a2`) makes the recruiter primary
  in all modes when a provider is configured. The planner sees the full
  workforce via `_compact_planner_prompt`. Proven live: codex-cli 0.145.0
  planned a 4-unit review+security decomposition.
- [x] **Deterministic code enforces coverage, eligibility, composition, and budgets.**
  `staffing_verifier.verify_staffing` enforces typed coverage, authority,
  composition rules, and per-unit/per-team budgets. `StaffingBudget`
  limits selection.
- [x] **Disabled and unavailable semantic winners are visible but never activated.**
  `disabled_shadows` and `unavailable_shadows` surfaces disabled/unavailable
  candidates without selecting them. Verified in
  `test_workforce_selection_safety.py`.
- [x] **Offline (no provider) declines rather than selecting a keyword-luck pick.**
  ADR-0087: offline (no provider) returns `_declined_outcome` (commit
  `ee47985`) — Agency injects no specialist and produces no Agency value rather
  than a wrong pick. The deterministic plan-and-staff decider survives as an
  eval baseline only, never as a runtime selection path. Deterministic code in
  the runtime path is recall plus validation, not a selection decider.

## AR-122: Governed contractor hiring and workforce lifecycle

- [x] **A proven real gap hires, enables, activates, and reports a contractor.**
  `hire_contractor_for_gap` builds, audits, enables, and activates a
  contractor from a declared unit gap. `_single_hireable_gap_unit`
  detects the gap in `pipeline.route`. Hiring tests
  (`test_workforce_dynamic_hiring.py`) exercise the full gap→admit→enable→
  activate→report path.
  - **Correction (previously overstated):** a FluxUI ask is NOT a genuine gap.
    `senior-developer` is the real FluxUI specialist — FluxUI appears in its
    `preferred_when` ("a Laravel, Livewire, or FluxUI repository needs a
    substantive product feature") and reaches the recruiter via the
    `scope_qualifiers`←`preferred_when` fallback (`contract.py:442`). The
    documented blocker for complex/multi-unit asks was nomination *validation
    rejection* in `_proposal_from_nominations`, not a real capability gap; the
    WP1/WP2 fixes (trust the model's eligible required nomination) address it.
    A genuine gap is one where no eligible specialist covers the typed unit.
- [x] **Duplicate gaps amend a coherent worker; unsafe merges are rejected.**
  `test_workforce_dynamic_hiring.py` covers: coherent gap amend,
  authority-escalation rejection, duplicate-covering-worker prevention,
  restaff without repeating inference.
- [x] **Known contractors are audited, enabled, visible, and exercised.**
  `install_known_contractors` seeds audited contractors;
  `test_known_contractor_install.py` verifies the install path.
- [x] **Promotion removes only the display moniker and preserves identity/history.**
  `_auto_promote_if_ready` and `promotion.py` enforce independent
  acceptance receipts. `test_workforce_promotion.py` verifies identity
  and history preservation.

## AR-123: Complete workforce CLI and live dashboard operations

- [x] **Every lifecycle operation is available in CLI and dashboard.**
  CLI: `cmd_workforce_list`, `cmd_contractor_list`, `cmd_workforce_show`,
  `cmd_workforce_search`, `cmd_workforce_duplicates`, `cmd_workforce_consolidate`,
  `cmd_workforce_transition`, `cmd_hiring_list`, `cmd_hiring_show`,
  `cmd_hiring_approve`. Dashboard: workforce grid, detail panel, hiring
  panel, lifecycle action form.
- [x] **Protected resident managers cannot be disabled.**
  `PROTECTED_AGENT_SLUGS` enforces; `test_agent_activation.py` verifies
  the protected error.
- [x] **Destructive actions require explicit confirmation and current generations.**
  `_confirmation` requires exact `--confirm` phrase and current revision;
  `test_workforce_cli.py` verifies.
- [~] **Live UI remains responsive, accessible, reduced-motion safe, and fully tested.**
  97 dashboard UI tests pass. Coverage is 96% lines / 95% branches (PR #129
  added workforce lifecycle UI branches not yet fully covered — follow-up).
  Reduced-motion CSS tested. Accessibility patterns verified.

## AR-124: Lifecycle assurance, native delegation, and provider evidence

- [x] **Assurance agents activate only after their required artifact exists.**
  `lifecycle_dispatch` gates assurance activation on artifact existence.
  `test_native_child_lifecycle.py` verifies the gate.
- [x] **Conflicting methods never share a forbidden context.**
  `same_context_conflicts` in `CompositionContract` + `_composition` in
  `verify_staffing` reject forbidden co-selection.
- [x] **Planned native children consume one-use parent activations without rerouting.**
  `_handle_native_child_pre_tool_use` injects one-use specialist prompts;
  `consume_delegation_activation` burns the receipt.
  `test_delegation_activation_receipts.py` (27 passed) verifies.
- [x] **Provider/router/actual-model evidence is accurate across every supported host.**
  `_record_workforce_model_receipts` persists provider, requested model,
  actual model, and receipt source. `test_workforce_attempts_persist_router_
  alias_and_reconciled_actual_model` verifies. Codex/Claude/OpenClaw/Hermes
  all carry correlation (b75df20 closes the Codex/Claude UserPromptSubmit
  parent-correlation gap).

## AR-125: Workforce selection and one-shot application evaluation

- [x] **Every worker passes positive, hard-negative, qualifier, shadow, and
      eligibility cases.**
  `test_every_worker_contract_has_positive_negative_shadow_and_eligibility_evidence`
  iterates the full snapshot — all 263 bundled specialists + 9 known
  contractors (asserts `worker_count == 272`) — and verifies positive
  selection, hard-negative (`not_for`), disabled-shadow, and live-eligibility
  for each. Plus 22+ scenario tests for representative workers. Full per-worker
  coverage is no longer a follow-up; it is green.
- [x] **Pairwise invariants and curated lifecycle teams pass.**
  Composition, coverage, and team-formation invariants verified via
  `verify_staffing`. Curated lifecycle teams in `test_workforce_dynamic_
  hiring.py`.
- [ ] **All representative one-shot applications pass outcome-based grading.**
  BLOCKED on a configured provider: one-shot app evaluation requires live
  inference runs with independent grading. The deterministic validators
  (`agency_runtime/core/evals/product_*`) and the eval harness
  (`agency eval routing`) run clean, but the graded one-shot trials need a
  live provider, which is not configured in the current environment.
- [ ] **Windows/Linux artifacts and all four host contracts pass before release.**
  Artifact smoke passes on both OS in CI. Four-host + ZCode canaries are a
  release-gate follow-up requiring live host sessions (WP8).
