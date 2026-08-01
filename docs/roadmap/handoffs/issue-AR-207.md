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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-217-bind-gap-evidence-to-hiring-critic
evidence_commit: 9c2e9f8f9a687998c331d6081016a15d1816fc36
minimum_ledger_commit: ad97037ff36ae712707a2e93a07197d77732108b
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 215 merged AR-215 as exact commit `9c2e9f8`; package
  `0.1.0+g9c2e9f8f9a68` is installed from that immutable revision.
- Bare install selected exactly Codex, ZCode, and dashboard. ZCode is current,
  Codex is registered, and the dashboard is active and reachable.
- Supported autonomous activation for `9c2e9f8` passes with an inferred
  `code-reviewer`, one completed delegation, a valid first header, zero
  corrections, autonomous hook bypass, and no persistent profile change.
- Trial `ar215-9c2e9f8-readme-01` is consumed and terminal `NO-GO` during
  contractor criticism. Planner and recruiter inference apply, but no route,
  specialist, delegation, header, or workspace write commits.
- AR-216 records the separate PR 213 all-scenario path-extraction finding.
  AR-217 owns only the live hiring-critic evidence handoff and has 32 focused
  tests green on its uncommitted implementation slice.

## completed-evidence

- AR-215's exact local gate passed: 642 Python production-spine tests passed
  with six skips, 110 dashboard UI tests passed, every routing-eval gate
  passed, and decision conformance killed all 73 mutations with zero invalid or
  surviving cases.
- Exact `9c2e9f8` activation session
  `019fbbd1-0427-7433-bf56-dfba9f7df5f0`, trace
  `019fbbd1-0d2a-7252-9d26-501525732b62`, run
  `95de670a-5bac-4fbe-94c9-d7b390771dc4`, and route
  `9bb4313a-1b2e-457f-a33e-bbde840c6947` passed in 133.9 seconds. It retained
  one `code-reviewer` load, grant, consumption, native worker, completed
  delegation, accepted finalization, valid first header, and zero corrections.
- Product trial `ar215-9c2e9f8-readme-01` is terminal `NO-GO` after 166.4
  seconds. Session `019fbbd5-5898-7a61-a5f9-e43888769741`, trace
  `019fbbd5-590e-7953-8ccb-be57cd49c39f`, and run
  `be99a177-3440-4bba-8886-7e0873348aeb` retain
  `substantive_specialist_unavailable` plus hiring codes
  `gap_not_independently_verified`, `evidence_is_self_asserted`, and
  `nearest_worker_comparison_not_credible_without_verification`.
- Trial atomicity preserves zero route, plan, specialist, grant, delegation,
  worker, finalization, header, or workspace-write evidence. Planner and
  recruiter inference both applied through `codex-subscription/gpt-5.6-luna`.
  Correction count zero is not success because parent generation never began.
- Code review proves both critic prompts omit the upstream verifier projection
  and complete workforce that candidate generation receives. The final critic
  therefore has only candidate-authored gap evidence to distrust.
- AR-217 adds identical runtime-projected evidence to the original and repair
  critic prompts without adding the raw request, changing selection authority,
  or weakening the four-call and second-rejection boundaries. Its exact local
  gate passes 643 Python tests with six skips, 110 dashboard UI tests, every
  routing gate, and 73/73 killed mutations with zero survivors or invalid
  cases and `source_unchanged=true`.

## exact-blocker

The independent critic cannot verify a gap from candidate-authored evidence
alone. AR-217's evidence handoff must pass review and the named local spine
before one new exact build may receive one activation and one product trial.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. The critic remains
independent and veto-only; local code may project evidence but may not author,
edit, or approve a contractor. Do not rerun consumed activation or trial
evidence, run more provider comparisons before the local gate, mutate private
trust state, label bypass as trust, dispatch hosted Actions, or touch the
owner's two untracked files.

## next-bounded-work-package

1. Finish at most two AR-217 review passes and the named fast production spine.
2. Create the substantive and ledger commits; inspect exact-head PR review and
   merge without hosted Actions.
3. Install the exact merge; run one activation and at most one product trial,
   then update the local evidence page and OpenClaw handoff.

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
- Exact builds `e62d0adc`, `1694d6e`, `d6ba36a`, and `9c2e9f8` have consumed
  their governed live evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
