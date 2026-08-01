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
  - docs/analysis/2026-07-31-ar-212-readme-story-evidence.html
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-215-repair-contractor-critic-rejection
evidence_commit: d6ba36a50a7d0e9186938e3b1a0b4330fd553aa0
minimum_ledger_commit: 83d1ba9b720ef2edf9abb176721e02d41dc20c84
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 213 merged AR-214 as exact commit `d6ba36a`; package
  `0.1.0+gd6ba36a50a7d` is installed.
- Bare install selected exactly Codex, ZCode, and dashboard. ZCode is current,
  Codex is registered, and the dashboard is active and reachable.
- Supported autonomous activation passes with an inferred `code-reviewer`, a
  completed delegation, a valid first header, zero corrections, and no
  persistent trust-profile change.
- The one exact-build product trial is consumed and fails earlier in workforce
  routing. Both bounded model comparisons reach an explicit gap, but no
  contractor survives hiring. AR-215 owns that isolated boundary.
- AR-215 now has a tracker, ADR, focused inference-owned repair, and 103 green
  hiring/config tests. No additional provider or host trial has been run.

## completed-evidence

- Exact `d6ba36a` activation session
  `019fbb8a-3ef8-7543-8df1-439007b0844f`, trace
  `019fbb8a-4c87-7f60-863a-2ab140dbe4e5`, and run
  `62d2cb5f-ba31-438b-905b-9a81f209bbff` passed in 123 seconds. It retained the
  route, plan, specialist load, grant, consumption, native child, worker run,
  completed delegation, and accepted finalization.
- Product trial `ar214-d6ba36a-readme-01` is consumed and terminal `NO-GO`
  after 134.7 seconds. Session `019fbb8c-8039-7a10-9b18-52f6a0378dce`, trace
  `019fbb8c-80ad-7351-a17f-5f4b1c024830`, and run
  `84ab3f57-8d6b-414b-9da8-59b7c3231681` retain a content-free
  `stage=routing`, `reason_code=routing_failed`, and
  `exception_category=validation_error` terminal receipt.
- Trial atomicity leaves zero route, plan, specialist, grant, delegation,
  worker, finalization, header, or workspace-write evidence. Codex exits zero,
  but the Agency preflight is correctly graded failed. Correction count zero
  is not success because parent generation never starts.
- A same-request Luna/low diagnostic authors eight units, applies planner and
  recruiter, declares a documentation-unit gap, and spends the two-call hiring
  budget on a valid candidate plus a critic rejection. The four retained
  critic codes are content-free contract-quality findings.
- A bounded Sol/xhigh comparison also authors eight units and reaches a gap,
  then returns `hiring_inference_failed`. The model mismatch is real but is not
  the product root cause. No more model-backed diagnostics are authorized for
  this package before local repair evidence.
- The AR-215 implementation reserves a four-call candidate, critic,
  replacement, critic sequence. The original hiring input plus allowlisted
  reason codes reaches one complete inference-authored replacement; local code
  never edits or accepts a rejected contract.
- Focused hiring/config verification passes 103 tests. Ruff lint, format, and
  `git diff --check` pass on the implementation slice.

## exact-blocker

The default two-call hiring budget makes a critic rejection terminal. AR-215's
four-call bounded repair must pass review and the named local spine before one
new exact build may receive one activation and one product trial.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. A critic may reject
and constrain one replacement but local code may not author it. Do not rerun
any consumed activation or trial, run more provider comparisons before the
local gate, mutate private trust state, label bypass as trust, dispatch hosted
Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Finish AR-215 focused review and the named fast production spine.
2. Create the substantive and ledger commits; inspect PR review evidence and
   merge the exact head.
3. Install that build; run one activation and one product trial, then update
   the local evidence page and OpenClaw handoff.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_ar214_context_delivery_authority.py -q -W error
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
- Exact builds `e62d0adc`, `1694d6e`, and `d6ba36a` have consumed activation and
  product trials.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
