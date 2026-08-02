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
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: 62ea12a2f8b1e0ed6fef6b869b2ab7134ba9aa3f
minimum_ledger_commit: 44faf748432b125fb0d652a3ab696f839f1bf5fe
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.` Prior exact
  `43870c8` proves activation, inference staffing, one contractor hire, and an
  eight-unit product topology, but its product workers acknowledged rather than
  executed and produced no workspace proof.
- AR-223 separates activation from execution. Exact `a2d1a7c` proves the second
  child turn but exposes encrypted child evidence. Repair `65ee298`, merged as
  `5ff4a08`, binds byte-equal parent/child ciphertext without retaining it and
  passes the complete named local gate. Bare install proves exact package
  provenance, Codex and ZCode registration, and a reachable dashboard.
- The one `5ff4a08` activation is consumed. Session
  `019fbf98-e5d8-77e3-9faf-0b9d36eeffb5`, trace
  `019fbf98-f1f4-77e3-82c5-8b7a065657cb`, run `76cb3c09`, route `0cec20a3`,
  finalization `8457f9c2`, and child `019fbf99-d680-7541-b951-00b6bd432b38`
  prove inferred `code-reviewer`, spawn, both waits, exact follow-up and child
  execution, accepted finalization, valid first response, and zero corrections.
  Autonomous trust bypass worked and persistent trust was unchanged.
- Activation still fails because `worker_runs.ended_at` is null. Current Codex
  fires `SubagentStop` after the activation turn but not after `followup_task`.
  Tests fabricated that second callback. No product trial ran.
- The bounded repair now reconciles the exact completed child at parent `Stop`
  from the documented parent transcript path. The activation stop stays open;
  execution must precede one nonempty turn-bound final response and matching
  completion. Forty-four focused tests pass without a synthetic second stop.
- Read-only reprojection over the consumed `5ff4a08` parent and child rollouts
  returns `completion_observed=True`. Two reviews are complete; they require
  exact lineage and place execution inside the second turn before its response.
- Exact `62ea12a` passes the named gate: Python 656/6, dashboard 110/110,
  628-document validation, repo-wide Ruff and routing, plus 90/90 killed
  decision mutations with zero invalid results and unchanged source.

## completed-evidence

- Two AR-221 reviews and 127 focused tests pass. Three new decision mutations
  are killed with zero survivors or invalid results and unchanged source.
- The named Python production spine passes 656 tests with 6 skipped. Dashboard
  UI passes 110 tests; 623 Markdown documents pass; repo-wide Ruff lint and
  format pass; routing passes every threshold; and decision conformance kills
  84 of 84 mutations with zero survivors or invalid results and unchanged
  source.
- The ciphertext repair passes Python 656/6, dashboard 110/110, 627-document
  validation, repo-wide Ruff lint and format, every routing threshold, and
  decision conformance 86/86 with unchanged source.
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

The README main story remains NO-GO pending PR/merge/install and one new
immutable-build activation. The locally green repair closes only an exactly
proven follow-up worker at parent `Stop`; no live evidence has consumed it yet.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Open and merge the locally green parent-stop repair, then install its exact
   immutable merge.
2. Spend one activation; only after it passes, spend one product trial.

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
  live evidence; exact `ba76ce7`, `a2d1a7c`, and `5ff4a08` also consumed their
  activations; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
