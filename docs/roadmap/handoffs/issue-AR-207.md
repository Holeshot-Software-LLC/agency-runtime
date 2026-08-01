---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-08-01
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-211-bound-immutable-commit-resolution.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/issue-AR-216-preserve-required-product-scenario-files.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/analysis/2026-07-31-ar-212-readme-story-evidence.html
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0133-treat-product-specialist-loads-as-turn-scoped.md
  - docs/decisions/0134-bind-contractor-risk-to-validated-authority.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-codex-child-task-activation
evidence_commit: 43870c8b3052c1b274de396576a399b2cb542e61
minimum_ledger_commit: 7046ee31b4c53b2a7005ceed44692fa738717adc
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 227 merged exact `43870c8`; that immutable build is installed.
- Default Codex, ZCode, and dashboard installation passes; the dashboard is
  active and reachable. Autonomous activation passes with one inferred
  `code-reviewer`, one real child, a valid first header, and zero corrections.
- Trial `ar221-43870c8-readme-01` accepts eight inference-authored units,
  applies one new contractor hire, and completes all eight native children,
  grants, delegations, worker runs, and current Codex waits.
- AR-221's exact scope and proof-token delivery is present in the responsible
  workspace-write child's goal. The workspace still remains empty because a
  Codex V2 spawn turn can complete after acknowledgement without executing its
  initial task. AR-223 freezes the next package around only that boundary.
- AR-223's reviewed local repair makes the first turn activation-only, claims
  one exact `followup_task` execution envelope, and requires its later child
  turn before a worker passes. Focused warning-strict slices pass 106, 176, and
  36 tests (318 total); the invalid 304-second aggregate timeout is not counted.
  The complete named local fast gate passes, including Python 656/6, dashboard
  110/110, and decision conformance 84/84 with zero invalid results. Issue 228
  and PR 229 record merged exact `ba76ce7`; that revision is installed. Bare
  installation passes dashboard and ZCode. Its consumed Codex canary selects
  `code-reviewer`, then records spawn, activation wait, and follow-up before
  Agency rejects its generated execution envelope. No second wait or header
  exists; corrections are zero and no product trial ran.

## completed-evidence

- AR-220 passes two reviews, focused 37, Python 656/6, dashboard 110/110,
  routing 39/39, and decision conformance 81/81 with unchanged source.
- Activation session `019fbe07-84b8-7bd3-b5d9-a6fe2ff7b713`, trace
  `019fbe07-8d3a-7870-ab40-f7e257ac5a67`, run
  `eb8c605e-11ad-4dfb-aa9b-fa9222f5ab09`, and route
  `6b4506f8-7715-47f6-80fe-8a9b75b7488d` pass under autonomous bypass without
  persistent trust changes.
- Product session `019fbe0a-4e75-7bb0-a1e2-1a2a54e2415a`, trace
  `019fbe0a-4f10-76d1-ba75-9e8615706dd0`, run
  `28c98413-c312-41fa-be2d-33479b226090`, route
  `6e4e32fe-92a2-41f5-b0d3-499d4e9b64a9`, and finalization
  `8ecffcc4-7d17-40e9-a43b-1cf5ca039d2d` retain the seven-unit boundary.
- The exact diagnostic is `product_wait_arguments_invalid`: seven spawns,
  seven waits, fourteen outputs, seven child starts, twenty-three messages, and
  zero unexpected items. Correction count is zero, but no first header, write,
  artifact, or validation is accepted.
- Unit `unit-34912a488e` is persisted as `workspace_write`; its exact reconstructed
  goal hash matches Store evidence, but its child-visible goal omits that scope.
- No hiring case exists for this trace. Existing contractor versions executed;
  AR-220's repaired four-call hiring path remains live-unproven.
- Two AR-221 reviews and 127 focused tests pass. Three new decision mutations
  are killed with zero survivors or invalid results and unchanged source.
- The named Python production spine passes 656 tests with 6 skipped. Dashboard
  UI passes 110 tests; 623 Markdown documents pass; repo-wide Ruff lint and
  format pass; routing passes every threshold; and decision conformance kills
  84 of 84 mutations with zero survivors or invalid results and unchanged
  source.
- Exact `43870c8` activation session
  `019fbe5e-a6da-72f3-ae6d-def468708e95` passes with one inferred
  `code-reviewer`, a valid first header, and zero corrections.
- Product session `019fbe61-6267-7581-ada8-44d157c989e4`, trace
  `019fbe61-62eb-7193-8ffd-e6f702c5271e`, run
  `8c16f792-6941-4e54-b41b-ee4594976953`, route
  `8d0ea8e3-9aef-40dd-9c1c-3a657510393c`, and finalization
  `469f75a4-c422-4893-8a8d-ae0c604014ca` retain the eight-unit boundary.
- The applied hiring case is `69bc7370-6763-4f41-966b-0b4af5215b54` for
  `python-cli-architecture-specialist`. This is the first accepted live proof
  that the repaired hiring path changes the workforce.
- Product collaboration reports eight spawns, eight waits, eight completed
  children, zero timed-out waits, zero failed children, and zero unexpected
  items. The header is valid with zero corrections, but the proof file and all
  artifacts are absent, so validation is skipped and the trial fails only
  `workspace_write_not_proven` / `proof_file_missing`.

## exact-blocker

The README main story remains NO-GO. Exact `ba76ce7` passes installation and
inference-owned selection, but Agency rejects its generated execution follow-up
before the Store claim. The consumed canary has no second wait or valid header,
and no product trial ran. AR-223 owns that exact hook boundary.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Repair only the exact `PreToolUse` follow-up matching failure.
2. Merge and install one fresh immutable build, then spend one activation.
3. Only after it passes, spend one product trial and update final evidence.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_inference.py tests/test_workforce_dynamic_hiring.py -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
.venv\Scripts\agency.exe eval routing --json --no-details
.venv\Scripts\agency.exe eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Product host remains sandboxed to the exact trial workspace.
- Only Codex, ZCode, and dashboard are in machine scope.
- One live product trial per exact installed build; any correction is failure.
- Exact builds `e62d0adc`, `1694d6e`, `d6ba36a`, `9c2e9f8`, `8cfd975`,
  `f8e607d`, `386afca`, `5c45f154`, `ff39761`, and `43870c8` consumed governed
  live evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
