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
evidence_commit: 35e1db588cbf280323cff0fd754e667bb91877cd
minimum_ledger_commit: e63488d34acb6d4420c88a72b6608a1ee666f985
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
- Commit `57f82c7` implements the source package. Commit `35e1db5` repairs the
  sole stale fast-spine fixture; `e63488d` is its exact worklog/roadmap ledger.
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
- The complete decision-conformance evaluator passed its baseline and killed
  all 42 curated mutations with zero survivors, zero invalid mutations, and an
  unchanged source checkout.
- The named warning-strict fast spine passed 636 tests with six intentional
  skips after its sole stale fingerprint fixture was made production-shaped.
- Markdown metadata checked 571 documents; policy availability, documentation,
  worklog, Ruff, formatting, routing evaluation, dashboard UI, and whitespace
  gates all pass.
- Owner-untracked `docs/analysis/2026-07-25-deep-audit-findings.md` and `uv.lock`
  remain untouched.

## exact-blocker

The locally verified source package has not yet been pushed, reviewed, merged,
or installed. No exact-installed Codex product trial has been attempted for
this build.

## same-task-continuity

Continue in this task. Do not dispatch hosted Actions while GitHub spending is
unavailable. Use local verification and stop at the first terminal boundary.
Do not ask the owner to restart Codex until the exact merged build is installed
and all pre-live gates are green.

## next-bounded-work-package

1. Push, open the PR, address only review findings that invalidate this package,
   and merge.
2. Install the exact merged build for Codex, ZCode, and dashboard, then run one
   supported trust-bypassed Codex trial with zero response corrections.
3. Generate the local shareable evidence report and OpenClaw handoff.

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
