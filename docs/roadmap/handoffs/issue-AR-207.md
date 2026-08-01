---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-211-bound-immutable-commit-resolution.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-212-repair-recruiter-verification
evidence_commit: e62d0adc6daaf91f99bdc125217a523665d1dad4
minimum_ledger_commit: 05bc8665f1c4024f9a3cdf16113020908e5141b0
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 204 merged the exact Codex delegation repairs as `207b150`.
- PR 207 merged AR-211 as `e62d0adc6daaf91f99bdc125217a523665d1dad4`
  after both Codex review threads were addressed and resolved.
- Exact official build `0.1.0+ge62d0adc6daa` is installed. Its planner resolves
  the formerly rejected `207b150` target and reports `e62d0adc` as current.
- Bare install discovered only Codex and ZCode and selected the dashboard.
  ZCode completed, the dashboard is active and reachable, and Codex registered.
- Supported autonomous activation passed. Product trial
  `ar207-e62d0adc-readme-01` is consumed and terminal `NO-GO`.
- AR-212 is implemented locally: verifier rejection now participates in the
  existing one recruiter repair, unsafe results are not cached, explicit gaps
  remain hireable, and preflight failure schema v2 retains bounded staffing
  and hiring reason codes.

## completed-evidence

- Default install dry-run selected exactly Codex, ZCode, and dashboard. The
  applied transaction created no other host integration.
- Dashboard scheduled-task registration is owned, current, active, reachable,
  and has no definition drift. No operator-presence ceremony was required.
- Autonomous activation session `019fbad0-9d80-70d0-8532-d1f49ff55df2`,
  trace `019fbad0-b2a3-7e93-b746-ac137b842b37`, and run
  `36d985a9-0e84-4e1e-9733-995bd1bb1d28` passed in 147.1 seconds.
- Activation inferred `code-reviewer`, persisted one route, plan row, grant,
  consumption, specialist load, native child, worker run, completed delegation,
  and accepted finalization. The first header was valid and corrections were
  zero. Trust was `autonomous_bypass`; persistent trust did not change.
- Product session `019fbad4-6358-70e1-856f-ec89d5c7ecd2`, trace
  `019fbad4-63d2-7e23-a688-ba3a21353de3`, and run
  `65525f38-914f-450d-ac4e-8145e4a5eca6` failed after 111.1 seconds.
- Planner and recruiter both recorded `structured_response_applied` on
  `gpt-5.6-luna`, but zero route, plan binding, specialist, delegation,
  finalization, header, or workspace write followed. Preflight reason was
  `substantive_specialist_unavailable`; correction count was zero.
- The exact 1,962-character executed prompt hash is
  `7ae24437002a7ea68da7f05e236ac8a88d214bf2ad79d8fd349c1a9b041660da`.
  One read-only route diagnostic immediately accepted an eight-unit team:
  `codebase-onboarding-engineer`, `python-application-engineer`,
  `software-test-engineer`, `code-reviewer`,
  `application-security-engineer`, `application-integration-verifier`,
  `technical-writer`, and `code-reviewer`.
- Source inspection proves full staffing verification occurs only after the
  recruiter response is marked applied and cached. Verifier rejection therefore
  cannot spend the existing second semantic attempt. The failure receipt also
  omits safe staffing and hiring reason codes.
- AR-212 tracker is https://github.com/Holeshot-Software-LLC/agency-runtime/issues/208.
  ADR-0129 freezes one verifier-driven repair attempt with no deterministic
  selector and bounded reason projection.
- The exact AR-212 acceptance slice passes 8/8. Canary/CLI compatibility passes
  24/24 and dashboard UI passes 110/110. Lint and formatting checks pass for
  every changed Python file.
- A broader preflight module run reached 98 passes and exposed an unrelated
  stale-token/native-plan-scope failure. It is recorded as AR-213 / tracker
  https://github.com/Holeshot-Software-LLC/agency-runtime/issues/209 and is not
  part of this bounded repair.
- Builds and trials `cc322381`, `f0fde9ee`, `6b49f17d`, `5ad4aef`,
  `dd85e7d`, `584b949`, and `e62d0adc` remain consumed.

## exact-blocker

The proven recruiter acceptance defect is repaired locally. The remaining gate
is procedural and live: pass the named fast spine, review and merge the exact
branch, install that merge, then run one new activation and at most one governed
product trial with workspace-write and zero-correction evidence.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Do not convert
verifier output into a deterministic team or inferred gap. Do not rerun any
consumed activation or trial, mutate private trust state, label bypass as trust,
dispatch hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Run the named local gate and stop on its first AR-212-relevant failure.
2. Review and merge one PR; keep hosted billing failures non-authoritative.
3. Exact-install the merge and run at most one activation and one product trial.
4. Produce the local evidence page and OpenClaw handoff.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused AR-212 boundary> -q -W error
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
- Exact build `e62d0adc` activation and product trial are consumed.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
