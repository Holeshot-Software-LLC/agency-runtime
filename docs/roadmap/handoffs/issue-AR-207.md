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
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: eb8e07770bf2b1d29933ff7730f09115928e4b1a
minimum_ledger_commit: 73274832a0985c7817c991061ac839386deb7cc1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` Exact installed
  merge `eb8e077` passes autonomous activation and routes the complete bounded
  inferred plan inline.
- Its consumed product trial `ar223-eb8e077-readme-01` accepts nine inferred
  units, loads seven specialists, completes nine delegations and workers,
  accepts one finalization, emits a valid first header, and needs zero
  corrections. It fails only `workspace_write_not_proven`: the exact workspace
  is empty despite three declared writer units.
- The first bounded diagnosis found that the execution follow-up carried only
  identity and told the child to recover its goal from the prior activation
  turn. The Agency-disabled control repeated that parent-only-context mistake,
  so it does not prove a sandbox defect.
- The local protocol repair carries the exact hash-bound goal in the execution
  turn, preserves shared-prefix compression, and rejects missing or tampered
  goals. ADR-0139 supersedes ADR-0136's content-free trigger premise.
- Fresh native control `ar223-native-writer-self-contained-01` is consumed. It
  completes in 42.4 seconds with exit zero under autonomous bypass but records
  zero spawns, zero follow-ups, one wait, and zero unexpected items. Its exact
  workspace is empty, so the self-contained child block never reached a child.

## completed-evidence

- PR 234 merges `eb8e07770bf2b1d29933ff7730f09115928e4b1a`; installed uv
  provenance and `agency version --json` match it. Bare installation discovers
  only Codex and ZCode and leaves the dashboard installed, active, current, and
  reachable.
- The consumed activation proves inference, one loaded specialist, exact
  spawn/follow-up/two-wait execution, a closed exit-zero worker, valid first
  header, zero corrections, and autonomous trust bypass without persistent
  profile mutation.
- The self-contained execution slice passes 54 focused delivery/plan tests and
  110 broader Codex lifecycle/product-host tests. Targeted Ruff lint and format
  checks pass. No new immutable build or product trial has been spent.

## exact-blocker

The README main story remains NO-GO. Consumed product trial
`ar223-eb8e077-readme-01` runs 698.421 seconds and proves a nine-unit plan,
seven loaded specialists, nine completed delegations, nine exit-zero workers,
one accepted finalization, a valid first header, and zero corrections. Its sole
failure is `workspace_write_not_proven`: all three declared writer workers have
empty stdout/stderr and the exact workspace has zero files. The trial must not
be rerun. The new native sentinel also remains NO-GO, but at an earlier exact
boundary: `codex_parent_spawn_missing`. It neither proves nor disproves child
workspace-write because no child was launched.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Preserve both consumed controls; do not rerun either exact workspace.
2. Repair or directly explain why the bounded native parent emitted one wait
   but no spawn despite the explicit self-contained delegation request.
3. Only after that focused boundary passes, run the named local gate, build
   once, and prove one Agency writer sentinel before any full product trial.

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
  activations; exact `b2be077` consumed both activation and product evidence;
  none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
