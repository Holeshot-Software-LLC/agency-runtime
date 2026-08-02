---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-08-02
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
  - docs/decisions/0142-require-terminal-product-child-before-next-unit.md
  - docs/decisions/0143-execute-codex-specialists-in-the-initial-spawn-turn.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0145-place-exact-codex-execution-after-specialist-expertise.md
  - docs/decisions/0146-preserve-content-free-codex-child-tool-outcomes.md
  - docs/decisions/0148-classify-nested-codex-exec-tools-without-content.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: 95aec42db22b3b45ecb706c7fb2ada9f0ae3d181
minimum_ledger_commit: e1c215719d8953efbbcf4ce176b593470dd0e1f8
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` The owner froze this
  package to the parent-finalization bug only. Repair `3b35ae0`, ledger
  `c8a0577`, and its one immutable candidate are consumed.
- The complete named gate passes: every docs/policy/Ruff/format check, 657
  Python passes with 6 skips, 110 dashboard passes, every routing correctness
  threshold after one bounded transient-latency classification rerun, and 99/99
  killed decision mutations with unchanged source.
- Exact `c8a0577cd60124eb8e29199c214bbeec81677349` builds canonically and
  independently verifies. Wheel SHA-256 is
  `f09e0c179a71f69c0c0ad07e0cfeb1fa1827a5c9e015364f33bb1c95c2fdadc1`;
  source SHA-256 is
  `f39e04851f86ed79fdeb227c9d97f04b65760356159cbf5baaedd85315dc5458`.
- Codex, ZCode, and the reachable dashboard install. Activation proves
  inferred/loaded/delegated `code-reviewer`, completed timestamped delegation,
  a terminal exit-zero worker, accepted finalization, autonomous trust bypass,
  and no persistent profile change.
- Writer `ar223-agency-writer-c8a0577-01` is consumed. The workspace is empty;
  its writer worker is unended and delegation is incomplete. The new guard
  truthfully terminates the run as `delegation_declined` with missing
  `delegation_execution`, replacing `d5a4e31`'s false `accept/completed` on the
  same incomplete shape. Scoped parent-finalization repair is `PASS`; README
  writer outcome remains `NO-GO`. Do not retry `c8a0577`.
- The next package isolates the Agency-only prompt-order boundary. Direct Codex
  writes with the same encrypted task transport and inherited workspace, while
  v3 left generic specialist refusal clauses after the exact action contract.
  ADR-0145 v4 keeps the specialist body hash-bound and places a byte-exact,
  fail-closed execution suffix last. Exact candidate `4c57507` passes the full
  named gate, builds and independently verifies, installs Codex, ZCode, and the
  dashboard, and passes autonomous Codex activation. Its one writer trial is
  consumed `NO-GO`: the child advances from zero to one tool call but creates
  no patch receipt or file. Do not retry `4c57507`.
- ADR-0147 implementation `2a19c79` durably attaches ADR-0146's validated fixed
  counts to each exact worker receipt before product admission. Snapshot rows
  expose `recorded`, `missing`, or `invalid`; missing writes remain unit-scoped
  failures. The focused suite passes 128 warning-strict tests, documentation
  validates 638 files, and repository Ruff/format/diff checks pass. No product
  trial ran in this slice.
- Clean head `e1c2157` passes the complete named gate: 638 docs, 610 formatted
  files, 657 Python passes with 6 skips, 110 dashboard passes, every routing
  threshold, and 102/102 killed decision mutations with unchanged source.
- Exact candidate `2bbd885` builds, verifies, installs Codex, ZCode, and the
  reachable dashboard, and passes one autonomous Codex activation. Its sole
  writer `ar223-agency-writer-2bbd885-01` is consumed `NO-GO`: Store v1 records
  three completed `functions.exec` wrappers and outputs, but the empty workspace
  proves no writer artifact. Nested tool classes remain unobservable.

## completed-evidence

- Activation session `019fc386-3a01-71f0-9477-f2f47c7ac47c`, trace
  `019fc386-47c4-71d3-bfd2-608e2dee51e0`, and worker
  `codex-agent:019fc387-1ec0-7712-9696-a97f941a097a` retain the pass.
- Writer session `019fc389-092b-7f30-b22c-a99ed0a3ec5e`, trace
  `019fc389-09a8-7600-9dd4-8dc624f33efb`, run
  `603ea506-d34b-418f-8e6a-2157b20afaa6`, delegation
  `7af31d7d-7561-4772-96ca-9380374740f4`, finalization
  `9c787ccc-11a6-4e7a-8d42-f43f35eccf1a`, and worker
  `codex-agent:019fc389-be08-7dc3-a4fe-7499e18e4890` retain the `NO-GO`.

## exact-blocker

Actual Agency child workspace execution remains unproven. ADR-0148 `95aec42` v2
now preserves nested tool classes and fixed wrapper outcomes without content;
focused tests pass. The named gate and one new immutable writer remain.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Complete bounded review, named verification, and one clean checkpoint.
2. Build one new candidate and consume one fresh writer sentinel. Never retry
   `c8a0577`, `4c57507`, or `2bbd885`; repair only its first proven boundary.

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
  `ae322ec`, `bffd2c8`, `b6bcdfb`, `d4c65a7`, `4d14b99`, `93e465a`,
  `d610630`, `7f0479f`, `be1ca0e`, `d5a4e31`, `c8a0577`, `4c57507`, and
  `2bbd885` consumed governed evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
