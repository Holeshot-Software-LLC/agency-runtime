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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-219-live-product-proof
evidence_commit: 386afca23bdc16e6c49c6dab55967b26a902a5b2
minimum_ledger_commit: 8646a61a8a3dd1bb6cb5ce5cc8e573a4efa81fcd
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 223 merged AR-219 as exact commit `386afca`; package
  `0.1.0+g386afca23bdc` is installed from that immutable revision.
- Bare install selected exactly Codex, ZCode, and dashboard. ZCode is current,
  Codex is registered, and the dashboard is active and reachable.
- Supported autonomous activation for `386afca` passes with an inferred
  `code-reviewer`, one completed delegation, a valid first header, zero
  corrections, autonomous hook bypass, and no persistent profile change.
- Trial `ar219-386afca-readme-01` is consumed and terminal `NO-GO`: planner and
  recruiter applied, then dynamic hiring required high-risk human approval and
  atomic preflight published no route, specialist, delegation, header, or
  workspace write. Correction count is zero and the workspace is empty.
- The exact next boundary is contractor risk authority, not topology: the work
  unit must own mutation scope and negated safety constraints must not become
  positive high-risk authority. Genuine high-risk authority stays gated.

## completed-evidence

- AR-217's exact local gate passed: 643 Python production-spine tests passed
  with six skips, 110 dashboard UI tests passed, every routing-eval gate
  passed, and decision conformance killed all 73 mutations with zero invalid or
  surviving cases and `source_unchanged=true`. Exact-head Codex review found no
  major issues.
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
- Repaired checkpoint `a347eff` passes 643 Python tests with six skips, all 110
  dashboard tests, 39/39 routing gates, and 73/73 killed mutations with zero
  survivors or invalid cases. The target budget mutation is killed and
  `source_unchanged=true`.
- PR 220 passed exact-head Codex review and merged normally as `f8e607d`.
- Exact activation session `019fbc48-be72-7442-9fa0-be195fcffffb`, trace
  `019fbc48-cb46-7c73-a835-23477439beb6`, and run
  `b1cfda5a-19c8-4615-8bd5-5c628053229a` prove one inferred and completed
  `code-reviewer` delegation, a valid first header, and zero corrections.
- Product session `019fbc4c-aeae-70c1-b256-f166e92452c5`, trace
  `019fbc4c-af63-76c0-9a40-55a559c4fee4`, and run
  `00c0ebd0-ca95-4da9-be01-e6ae848c82fb` retain eight completed workers and an
  accepted finalization. The product projection reports
  `native_collaboration_topology_invalid`; workspace proof and artifacts are
  absent.
- AR-219's two reviews and 102 focused tests pass exact reuse, conflicting
  identity rejection, child-goal delivery, sentinel ownership, and diagnostics.
- The branch passes Python 643/6, dashboard 110/110, routing 39/39,
  615-document validation, repository-wide Ruff, and diff validation.
- The full 73-mutation decision-conformance process completed after its outer
  shell deadline, but that shell did not retain the terminal JSON or exit code,
  so it is not claimed as fresh. Every changed production source passes a
  captured 22/22 slice with zero survivors/invalid and unchanged source.
- PR 223 merged the reviewed head as `386afca`; GitHub-hosted checks were not
  relied on or retried, and no GitHub Codex review arrived before merge.
- Exact activation session `019fbd75-2ea2-7f80-b6f7-eb2bb0724f2a`, trace
  `019fbd75-3d0b-7b10-a463-2b95ee1fe2ab`, and run
  `36b9b721-7efa-400d-9e07-ba1b860a1772` pass with one real specialist child,
  valid first header, zero corrections, and autonomous bypass.
- Product session `019fbd7a-0c24-7581-a49d-91bbe870f7ea`, trace
  `019fbd7a-0cb8-7dc0-ba1b-415d3d834a3e`, and run
  `6e03910a-ec8b-4c4a-8d15-f2700b7cd219` fail atomically at high-risk hiring;
  zero execution rows commit and exact isolated trust remains proven.

## exact-blocker

The README main story remains NO-GO. Exact `386afca` proves install and
activation, but its single product trial fails before routing because an
isolated-workspace contractor is treated as high risk. One bounded risk-
authority repair and one new immutable-build proof remain.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Both planner and
recruiter retain exactly one inference-authored repair; local code may reject
but may not fill either response. Do not rerun consumed activation or trial
evidence, run more provider comparisons before the local gate, mutate private
trust state, label bypass as trust, dispatch hosted Actions, or touch the
owner's two untracked files.

## next-bounded-work-package

1. Bind contractor mutation authority to the validated work unit and make risk
   classification distinguish explicit prohibitions from granted authority.
2. Run focused tests, two reviews, and the named fast gate; merge and install
   one immutable repair without relying on hosted Actions.
3. Spend one activation and at most one product trial on that new build, then
   update the local evidence page and OpenClaw handoff from the exact result.

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
- Exact builds `e62d0adc`, `1694d6e`, `d6ba36a`, `9c2e9f8`, `8cfd975`,
  `f8e607d`, and `386afca` consumed governed live evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
