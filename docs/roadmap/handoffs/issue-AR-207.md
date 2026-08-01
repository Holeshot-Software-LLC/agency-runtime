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
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-218-fund-stage-repairs
evidence_commit: 095e244a23aa42f6e38f282e3f1d902804e773de
minimum_ledger_commit: 095e244a23aa42f6e38f282e3f1d902804e773de
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 218 merged AR-217 as exact commit `8cfd975`; package
  `0.1.0+g8cfd9751aa72` is installed from that immutable revision.
- Bare install selected exactly Codex, ZCode, and dashboard. ZCode is current,
  Codex is registered, and the dashboard is active and reachable.
- Supported autonomous activation for `8cfd975` passes with an inferred
  `code-reviewer`, one completed delegation, a valid first header, zero
  corrections, autonomous hook bypass, and no persistent profile change.
- Trial `ar217-8cfd975-readme-01` is consumed and terminal `NO-GO` during
  workforce inference. Planner rejection/repair and recruiter rejection spend
  the entire three-call fast budget, so the bounded recruiter repair cannot run.
- AR-216 records the separate PR 213 all-scenario path-extraction finding.
  AR-218 owns only the composed planner/recruiter repair budget and is focused-
  green on its four-call implementation slice.

## completed-evidence

- AR-217's exact local gate passed: 643 Python production-spine tests passed
  with six skips, 110 dashboard UI tests passed, every routing-eval gate
  passed, and decision conformance killed all 73 mutations with zero invalid or
  surviving cases and `source_unchanged=true`. Exact-head Codex review found no
  major issues.
- Exact `8cfd975` activation session
  `019fbc03-2036-7070-9ca0-85f59db1e17a`, trace
  `019fbc03-2801-72c3-a362-0aa9f940143e`, run
  `d566091b-d87c-44b5-a280-d877511bae6b`, and route
  `a783aec5-edc1-45eb-868c-73c327fe898b` passed in 116.9 seconds. It retained
  one `code-reviewer` load, grant, consumption, native worker, completed
  delegation, accepted finalization, valid first header, and zero corrections.
- Product trial `ar217-8cfd975-readme-01` is terminal `NO-GO` after 101.1
  seconds. Session `019fbc05-3cf8-7b83-b6ca-1e280067f0a6`, trace
  `019fbc05-3d81-74a3-a532-ba613b2a7846`, and run
  `682ee08f-9663-466a-8d86-16fd01ea3492` retain planner rejection, planner
  repair, recruiter rejection, `workforce_inference_failed`, and
  `staffing=inference_invalid` through `codex-subscription/gpt-5.6-luna`.
- Trial atomicity preserves zero route, specialist, grant, delegation, worker,
  finalization, header, or workspace-write evidence. Correction count zero is
  not success because parent generation never began.
- The composed AR-218 regression now passes planner rejection/repair followed
  by recruiter rejection/repair in exactly four calls. Existing explicit lower
  budgets remain authoritative and no deterministic selection path was added.
- AR-218's named fast gate passes 643 Python tests with six skips, 110 dashboard
  UI tests, all routing gates, 612-document validation, repository-wide Ruff
  lint/format, and 73/73 killed decision mutations with zero survivors or
  invalid cases and `source_unchanged=true`.
- Exact-head PR 220 review found that a legacy balanced-only cap of three would
  be invalidated by the new omitted fast default. The focused-green repair caps
  the effective omitted fast value to that explicit balanced value while
  preserving the persisted partial document.

## exact-blocker

The local four-call repair is green. The compatibility repair must pass the
named gate and exact-head rereview before merge; no other implementation scope
is open.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Both planner and
recruiter retain exactly one inference-authored repair; local code may reject
but may not fill either response. Do not rerun consumed activation or trial
evidence, run more provider comparisons before the local gate, mutate private
trust state, label bypass as trust, dispatch hosted Actions, or touch the
owner's two untracked files.

## next-bounded-work-package

1. Checkpoint the compatibility repair, run the named gate once on that new
   head, resolve the exact review thread, and merge without hosted Actions.
2. Install the exact merge, deliberately set this machine's explicit fast
   budget to four, and run one activation plus at most one product trial.
3. Publish the local evidence page and OpenClaw handoff, stopping on any new
   first boundary rather than widening the package.

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
- Exact builds `e62d0adc`, `1694d6e`, `d6ba36a`, `9c2e9f8`, and `8cfd975` have consumed
  their governed live evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
