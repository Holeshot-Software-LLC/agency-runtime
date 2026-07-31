---
title: "AR-205 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [handoff, workforce, inference, hiring, hooks, stewardship]
related:
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-205
branch: codex/ar-203-activation-planning-contract
evidence_commit: 271e5a01d08b74dbe755662de997a32d04e5e735
minimum_ledger_commit: 37f6f9532fdc66c48a68f3b447fc0c3ffe482fbb
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/190
---

# AR-205 active recovery capsule

Bounded recovery projection for inference-owned exact-specialist staffing. The
[canonical issue](../issue-AR-205-make-default-manager-inference-safe.md) owns
acceptance; this capsule records only current proof and the next package.

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 193 merged exact revision `f0fde9ee929e13587f62dd85147cf63b18b5d37e`;
  exact build `0.1.0+gf0fde9ee929e` is installed.
- Current-profile supported-bypass activation selected `code-reviewer` through
  real inference and completed grant, load, native spawn/wait, delegation,
  worker run, and accepted finalization with zero corrections.
- The only product trial for that build, `ar205-f0fde9e-readme-01`, is terminal
  `NO-GO`; it reached `preflight_failed` after 101.1 seconds and left the
  workspace empty. Do not rerun that build.
- Exact-prompt private replay proves inference authored 11 specialized units
  and staffed 10. It explicitly declared the documentation unit uncovered, but
  gap hiring was never entered because the product harness was mistaken for
  the read-only activation canary.
- Owner-untracked `docs/analysis/2026-07-25-deep-audit-findings.md` and `uv.lock`
  remain untouched.

## completed-evidence

- A bounded live provider replay first reproduced the failure: planner repair
  still violated assurance ordering, then recruiter repair could not distinguish
  safe combinations from Python/TypeScript and documentation coverage gaps.
- After the repair, a fresh non-product replay accepted a nine-unit plan and
  nine specialist assignments: codebase onboarding; paired Python and
  TypeScript implementation; test authorship; correctness, security, and
  accessibility review; technical writing; documentation review; and test
  evidence analysis.
- The accepted outcome is `inferred`, recruiter status is `applied`, staffing
  has no abstention codes, and no deterministic unit or worker was inserted.
- Focused warning-strict verification passes 84 tests. Ruff check and diff
  whitespace are clean.
- Decision conformance passed its baseline and killed all 44 curated mutations
  in 328.7 seconds with zero survivors, zero invalid mutations, and unchanged
  source. The two new mutations prove planner acceptance constraints and typed
  uncovered-gap evidence must reach inference.
- The named fast Python spine passes 636 tests with 6 intentional skips;
  dashboard UI passes 110; routing evaluation 1.4.0 passes every gate;
  documentation validates 574 files; and Ruff checks all 602 Python inputs.
- The exact committed-tree decision-conformance rerun passed its baseline and
  killed 44/44 mutations in 327.7 seconds with zero survivors or invalid
  results and unchanged source.
- PR 192's first Codex review found three valid candidate defects. The repairs
  enforce the configured planner bound before recruitment, match positive
  release proof to the requested operation, and retain communication when the
  request names it. The second and final broad review found four additional
  valid P1s in compact-budget clamping, proof scoping, typed-recall size, and
  descriptive negation. All seven findings are repaired; the changed modules
  pass 83 tests and the wider safety boundary passes 115 with one intentional
  skip.
- Commit `271e5a0` constrains only the closed-world canary's unit count and
  artifact type; inference still selected `code-reviewer`. The fresh cloned-
  Store hook replay produced one accepted binding and assignment with immediate
  delegation. Focused tests pass 72 cases and two new decision mutations cover
  removal of either request-bound constraint.
- PR 193 merged that repair and native exact-installed activation is now green.
  Product preflight advertises repository-write, test-execution, and native-
  delegation capabilities; the remaining defect is the environment-wide
  early return that suppresses inference-declared contractor hiring.

## exact-blocker

No current build proves a specialist team, native delegation, workspace write,
product artifacts, and zero corrections in one end-to-end run. The immediate
blocker is now exact: preserve no-hiring behavior for the closed-world
activation task, but permit ordinary product preflight to hire the narrow
contractor that inference declared missing.

## same-task-continuity

Continue in this task and stop at the first terminal boundary. Do not dispatch
hosted Actions while GitHub spending is unavailable. Do not reinterpret a
passing direct routing replay as product success.

## next-bounded-work-package

1. Repair and verify activation-task-specific hiring suppression.
2. Merge, exact-install, prove native activation, then run one supported-
   bypassed product trial for only the new exact build.
3. Require zero corrections, a real specialist or hired-contractor chain,
   workspace-write proof, and product artifacts; then generate the local report
   and OpenClaw handoff.

## verification

~~~text
python -m pytest tests/test_workforce_intent.py tests/test_workforce_inference.py tests/test_decision_conformance.py -q -W error
python -c "from agency_runtime.cli.entrypoint import main; raise SystemExit(main())" eval decision-conformance --repository . --json
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
~~~

## constraints

- Inference is the only authority that may design, rank, select, or declare a
  gap for substantive specialist work.
- Deterministic code may expose typed recall and veto unsafe proposals; it may
  not synthesize a plan, choose a worker, or broaden a near-match.
- `agency-steward` is parent/evidence infrastructure and never a worker.
- The supported Codex trust bypass is labeled bypassed, never trusted.
- One live product trial per exact installed build; any correction is failure.
