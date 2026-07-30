---
title: "AR-199 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-29
tags: [handoff, codex, routing, workforce, evidence, recovery]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-199
branch: codex/ar-199-fbed-canary
evidence_commit: 9b50993215b4c800fe540632ca3a9f97ae6de91e
minimum_ledger_commit: 36d2ec67810eaffe014cc08a73402146276830d3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161
---

# AR-199 active recovery capsule

## checkpoint

- PR 172 merged the inference-owned selection repair as exact commit
  `9b50993215b4c800fe540632ca3a9f97ae6de91e`.
- The uv tool reports exact build `0.1.0+g9b50993215b4`; Codex bundle
  `0.1.0+codex.0fa5aeccbffe` is registered and enabled.
- First ordinary product trace `019fb03e-5ad6-7b70-8d22-bc8c7ee0d028` is a
  bounded `NO-GO`; its exact-installed repair is awaiting one rerun.
- Owner-untracked files remain untouched.

## completed-evidence

- Exact-installed isolated trace `019fb039-193d-79c2-b771-5cdd2ad86065`
  passes with one selected and loaded `code-reviewer`, one native spawn and
  wait, one completed delegation, worker exit zero, one accepted finalization,
  a valid first-pass header, and `correction_count: 0`.
- Its profile is explicitly isolated and uses Codex's hook-trust bypass; it
  does not claim current-profile trust or persist a current-profile attestation.
- Current-profile verification sees all eight hooks enabled but modified and
  stops before model invocation. That attended trust boundary remains open.
- The ordinary product trace persisted two successful Luna wrapper receipts
  and 53 eligible workers, but its nine-unit plan atomically abstained because
  `unit-architecture` had no eligible `architecture-record` / `design` owner.
- `b8c0a8d` compiles architecture roles with `architecture-record` / `design`
  coverage. `6ca745d` removes the temporary hard-coded architecture anchor and
  proves contract-based recall still includes `software-architect`.
- Audit found two violations of ADR-0088 in the configured-provider path:
  deterministic acceptance skipped the recruiter, and role anchors could
  replace or reorder inference nominations.
- `882b920` removes both online deterministic decision paths. Planner and
  recruiter now always run for a fresh configured-provider route; deterministic
  logic is limited to recall, safety vetoes, and the stamped no-provider floor.
- Cross-layer focused verification passes 175 tests with one platform skip and
  one expected xfail.
- The named Python spine passes 653 tests with 6 skips, all 109 dashboard tests
  pass, and every routing-evaluation gate passes; documentation, Ruff,
  formatting, and diff checks also pass on this exact source.
- Provider attempts remain CAS-atomic model receipts; inferred staffing gaps
  remain eligible for bounded governed hiring rather than silent fallback.
- Context telemetry was below the 50-percent clean-checkpoint threshold before
  this source/recovery checkpoint; no live rerun is allowed before its ledger.

## exact-blocker

The online inference repair is merged, exact-installed, and fast-verified. The
first ordinary trace remains `NO-GO` until one isolated-profile product rerun;
persistent-profile trust remains attended but does not block that rerun.

## same-task-continuity

Continue in this task. Do not rerun the passing isolated activation package.

## next-bounded-work-package

1. Rerun one bounded ordinary isolated-profile product proof and audit receipts.

## verification

~~~text
python -m pytest tests/test_host_hooks.py tests/test_preflight_bounds.py tests/test_store_preflight_coverage_final.py tests/test_workforce_inference.py tests/test_workforce_dynamic_hiring.py tests/test_codex_activation_canary.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_operator_presence.py tests/test_security_turn_boundaries.py -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
~~~

## constraints

- Preserve hook trust and exact native-child goal validation; never use a trust
  bypass as current-profile production evidence. The isolated canary may use
  Codex's explicit noninteractive hook-trust bypass inside its private profile.
- Preserve ready-CAS atomicity; do not hand an unscoped live Store to a planner
  that can leave partial routing or workforce writes.
- Do not rerun external-provider diagnostics without explicit egress approval.
- Preserve owner-untracked files.
- Do not create tracker issues or hosted workflows without explicit
  authorization.
