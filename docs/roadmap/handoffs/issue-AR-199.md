---
title: "AR-199 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-28
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
branch: codex/ar-199-restore-codex-workforce
evidence_commit: 6fc3173901af94d03f7d61a350a14892083e3735
minimum_ledger_commit: 3bb4c48be2e60cc16b24a600bfbc98011063fe62
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-199 active recovery capsule

## checkpoint

- Exact merged revision `6fc3173` is installed globally and registered in
  Codex and ZCode; the dashboard is active and reachable.
- Fresh Codex terminal trust completed and a fresh task received the current
  resident-manager kernel.
- The repair is on `codex/ar-199-restore-codex-workforce`; the owner-untracked
  analysis draft and `uv.lock` remain untouched.

## completed-evidence

- The first trusted production task proved a valid request-scoped binding for
  `agents-orchestrator` and `chief-of-staff`.
- The Store has 272 active workers, 97 runs, 85 routing decisions, zero model
  receipts, and one specialist-load row.
- A nontrivial revision turn required selection, ran two applied structured
  provider calls, planned four work units, and still produced no unit-agent
  plan. Its receipt records zero eligible workers and
  `hiring_store_unavailable`.
- Local workforce search proves relevant enabled Windows/Codex workers exist,
  including `multi-agent-systems-architect`, `python-application-engineer`, and
  `code-reviewer`.
- Source inspection proves preflight passes `store=None` to routing, so atomic
  ready commit is preserved while provider-receipt persistence and governed
  hiring are unavailable.
- The live activation canary passed hook-trust inspection, attempted one native
  spawn, and was rejected by Agency's own exact-goal validator. No retry or
  trust bypass ran.
- Provider attempts are now projected into the ready evidence and committed as
  model receipts only with the winning CAS; replay does not duplicate them.
- Governed hiring now stages validated contractor state, uses it for in-memory
  staffing and hydration, and commits the case, prompt, worker, and two hiring
  receipts inside the ready transaction. CAS loss leaves no workforce state.
- The ready transaction rechecks the daily hiring limit under its immediate
  write lock. A competing hire makes the staged commit fail and roll back.
- The Codex canary accepts the current opaque persisted spawn message only when
  its package-owned goal, parent scope, task label, and assignment already
  correlate. Ordinary goal mismatches remain denied.
- Focused verification passes: 76 routing, receipt, hiring, and canary tests;
  29 preflight-bound tests; and 7 durable-continuation tests with 6 platform
  skips.
- Context telemetry reported 49.0 percent remaining, so this source-and-focused-
  verification slice requires the substantive and ledger checkpoint before the
  fast spine and live evaluation.

## exact-blocker

End-to-end exact-installed Codex workforce execution is not yet proven. The
source repair and focused verification are complete; the remaining gates are
the named fast spine, merge, exact reinstall, live canary, and fresh-task
header/model/delegation evidence.

## same-task-continuity

Continue in this task after the recovery and ledger commits. Do not create a
new task or rerun the live canary until focused source verification passes.

## next-bounded-work-package

1. Finish the second bounded review pass and run the named fast spine.
2. Commit the repair and ledger, push, open and merge the PR.
3. Reinstall the exact merge and run the live Codex activation verifier.
4. Capture fresh-task resident-manager, specialist, delegation, and model
   receipt evidence for the handoff.

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
  bypass as production evidence.
- Preserve ready-CAS atomicity; do not hand an unscoped live Store to a planner
  that can leave partial routing or workforce writes.
- Do not rerun external-provider diagnostics without explicit egress approval.
- Preserve owner-untracked files.
- Do not create tracker issues or hosted workflows without explicit
  authorization.
