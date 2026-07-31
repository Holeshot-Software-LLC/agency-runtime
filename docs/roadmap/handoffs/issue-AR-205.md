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
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/worklog/2026-07-31-57f82c7-exact-specialist-every-task.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-205
branch: codex/ar-203-readme-story-final-proof
evidence_commit: 57f82c7f6502c907d0888e501ca57b0a64aa22f6
minimum_ledger_commit: 0452790bf1d84f93fe4911b35bd6bcbb50a6b6d0
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/190
---

# AR-205 active recovery capsule

Bounded recovery projection for replacing the universal generalist path with
inference-owned exact specialist staffing. The
[canonical issue](../issue-AR-205-make-default-manager-inference-safe.md) owns
acceptance; this file records only the current proof and next package.

## checkpoint

- The active goal remains `README's main story works in reality.`
- Commit `57f82c7` implements the source package; `0452790` is its exact
  worklog/roadmap ledger.
- `agency-steward` is the sole resident infrastructure identity and cannot be
  selected, loaded, or delegated as a domain worker.
- Recruiter inference defines the ideal role from an open-ended pool before it
  compares the installed roster. A gap may contain zero ranked roster cards.
- Ordinary task gaps create distinct narrow contractors. The legacy amendment
  switch is explicit and disabled for runtime task staffing.
- Substantive preflight fails before generation when staffing is empty and
  rechecks after isolated-plan normalization so a selected-but-unplanned
  identity cannot bypass the boundary.
- GitHub tracker
  [#190](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/190)
  records AR-205 under `epic:product`.

## completed-evidence

- Core routing/workforce verification: 166 passed.
- Preflight-boundary verification: 30 passed.
- Native Codex/Claude/ZCode hook verification: 94 passed.
- Adapter parity: 48 passed; header/store: 27 passed.
- MCP/ZCode/Claude compatibility: 64 passed with five intentional skips.
- Dashboard client: 110 passed.
- HTTP verification reached 98 passed with three intentional skips; its sole
  stale post-preflight assertion was corrected and the node passed directly.
- Ruff checked all Python sources, tests, and scripts. All 602 Python files are
  format-current; Markdown metadata checked 569 documents; diff whitespace is
  clean.
- Four new decision mutations and their named baseline tests pass: singleton
  steward, empty-candidate gap, distinct task specialist, and post-plan
  no-generalist enforcement.
- Owner-untracked `docs/analysis/2026-07-25-deep-audit-findings.md` and `uv.lock`
  remain untouched.

## exact-blocker

The source package is checkpointed but not yet fully admitted. The expanded
decision-conformance evaluator and named fast verification spine have not run
against `57f82c7`; no PR/merge, exact install, or live Codex product trial has
been attempted for this build.

## same-task-continuity

Continue in this task. Do not dispatch hosted Actions while GitHub spending is
unavailable. Use local verification and stop at the first terminal boundary.
Do not ask the owner to restart Codex until the exact merged build is installed
and all pre-live gates are green.

## next-bounded-work-package

1. Run the complete decision-conformance evaluator and named fast spine; repair
   only failures that invalidate exact-specialist staffing.
2. Update durable evidence, push, address PR review, and merge.
3. Install the exact merged build for Codex, ZCode, and dashboard, then run one
   supported trust-bypassed Codex trial with zero response corrections.

## verification

~~~text
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/verify_docs.py
python -m pytest tests/test_preflight_bounds.py tests/test_host_hooks.py -q -W error
python -m pytest tests/test_resident_managers.py tests/test_workforce_inference.py tests/test_workforce_dynamic_hiring.py tests/test_routing_correctness.py -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Inference is the only authority that may select or design a specialist for a
  substantive turn. Missing or invalid inference fails loudly.
- Deterministic code may recall candidates and reject unsafe proposals but may
  not select, broaden, or synthesize a worker.
- The roster is a reusable cache, not the boundary of possible expertise.
- The resident steward preserves scope and evidence; it never performs domain
  work or claims specialist activity.
- The supported Codex trust bypass must be labeled bypassed, never trusted.
- One live product trial per exact installed build; correction count greater
  than zero is failure.
