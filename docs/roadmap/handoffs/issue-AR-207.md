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
  - docs/decisions/0140-use-codex-stable-multi-agent-feature.md
  - docs/decisions/0141-admit-writer-proof-only-through-agency-plans.md
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
  `ae322ec` passes the named gate and default suite install. Codex autonomous
  activation is runtime-verified; ZCode is enabled; the dashboard is active
  and reachable.
- The older consumed product `ar223-eb8e077-readme-01` proves nine inferred
  units, seven loaded specialists, nine completed workers, a valid first
  header, and zero corrections, but no writer artifact.
- Direct app child `ar223-direct-native-child-01` independently proves exact
  current-host child workspace-write. Generic Agency-disabled controls remain
  non-admissible under ADR-0141.
- Writer sentinel `ar223-agency-writer-ae322ec-01` is invalid because its
  harness prompt states the wrong SHA-256. Its correct 23-byte hash is
  `767303371a040770ecccc894befc37191c57af167b1dce19ed569b5d20c3e5eb`;
  the same build must not be retried.
- That retained run independently proves a scheduler defect: an accepted
  five-row plan dispatches four children and advances while every prior worker
  remains nonterminal. Unit five is never launched before the 300-second host
  timeout and the writer proof is absent.
- ADR-0142 requires one terminal activation wait and one through three bounded
  execution waits. A commentary wake is not completion, and no later row may
  launch before the exact prior child is terminal.

## completed-evidence

- Exact `ae322ec` passes 657 Python production tests with 6 skips, 110 dashboard
  tests, every routing threshold, and 91/91 decision mutations. Its wheel and
  source archive pass strict metadata and independent exact-commit verification.
- Default installation discovers Codex and ZCode, installs both plus the
  dashboard, and records `trust_mode=autonomous_bypass`. Activation proves one
  inferred/loaded `code-reviewer`, one native worker, one accepted finalization,
  and zero corrections.
- The ADR-0142 focused slice passes 42 tests and both new decision mutations;
  the second and final surrounding lifecycle review passes 164 tests. Targeted
  Ruff passes; the named gate and new immutable live proof remain pending.

## exact-blocker

The README main story remains NO-GO. The new installed build proves activation,
but its writer sentinel is invalid due to the harness-authored hash mismatch.
The exact product defect now under repair is terminal ordering: the parent must
not advance after a commentary wake while the current writer is still active.
No corrected Agency writer artifact, full product, concise header, dashboard
configuration parity, or shareable final report is proven yet.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Run the named local gate for the reviewed ADR-0142 repair.
2. Build and install one new exact commit; do not reuse `ae322ec` evidence.
3. Run one corrected accepted-plan Agency writer sentinel. Stop before a full
   product trial unless exact file proof and zero corrections pass.

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
