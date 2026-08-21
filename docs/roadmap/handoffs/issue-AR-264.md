---
title: "AR-264 active recovery capsule"
status: active
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [handoff, contractors, hiring, prompts, workforce]
related:
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-264
branch: codex/ar264-exact-main-live-evidence
evidence_commit: e796b56b441c9906b9997188362951d9ba1fd73f
minimum_ledger_commit: 9f44c14209f9fcfc72c1338448027d8710c2990e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Worktree `C:\Workspaces\Holeshot Software\agency-runtime-ar264-rollout` is on
  `codex/ar264-exact-main-live-evidence`, based exactly on merged remote main
  `da851c65`. The primary checkout has unrelated owner WIP and is untouched.
- Context telemetry reads 23.9 percent remaining. The repair and its ledger are
  clean at `9f44c142`; this gate receipt now forms the next recovery checkpoint.

## completed-evidence

- PR #314 merged as `da851c65` with `[skip ci]`; `origin/main` has that exact
  merge and GitHub reports no run for it.
- Exact-main Claude bundle installation succeeded, but the Store correctly
  preserved all 15 workers because the v2 migration recognized only a
  synthetic canonical v1 predecessor. Codex, ZCode, dashboard installation,
  and all provider draws stopped at that evidence boundary.
- Real Store inspection proved 15 revision-zero malformed package versions.
  Fourteen matched the original contract projection; backend-service-engineer
  additionally required its earlier capability and evidence fields.
- The repair pins all 15 historical prompt hashes and reconstructs both the
  pre- and post-August-6 v1 identities. The Store transaction rechecks exact
  content, metadata, recruitment-contract bytes, and hash before staging v2.
- A disposable SQLite backup advanced 15/15 workers, was idempotent on pass two,
  retained two-version lineage throughout, and kept TypeScript at two accepted
  artifacts with one remaining for promotion. The real Store was byte-for-byte
  unchanged by the diagnostic.
- Dashboard API test projects `changed artifacts and focused verification
  results`; all 134 dashboard UI tests pass and no false evidence fallback is
  rendered for that worker.
- Focused predecessor tests cover both shipped v1 identities, backend replay,
  auditable historical hiring evidence, and fail-safe preservation of an exact
  prompt with amended recruitment metadata.
- The widened contractor, Store, installer, lifecycle, hiring, and selection
  suite reports 332 passed and one skipped in 247.07 seconds.
- All 14 governing local gates pass in 16.5 minutes: 806 passed and 20 skipped
  in the production spine, 695 matrix-evidence tests, 161 workflow-contract
  tests, 151 current mutation snippets, and 134 dashboard UI tests above the
  configured line, branch, and function coverage floors.
- Metadata covers 731 Markdown files, the policy projection and 1,085-row
  worklog are current, documentation validation and `git diff --check` pass,
  and deterministic routing passes every correctness, safety, performance,
  scale, and CLI-startup gate.
- GitHub issue #313 is open with the exact AR-264 title, canonical body, URL,
  and `epic:roster-governance` label. Repository-wide strict tracker checks
  still fail on pre-existing missing trackers and historical state/label debt;
  neither strict failure reports AR-264.
- Claude CLI remains logged out. That blocks paid Claude live smoke but not
  local repair verification or managed bundle installation.

## exact-blocker

The exact-main acceptance claim is not complete until this repair reaches main
and the real Store advances from package v1. Claude authentication is an
operator blocker for its later live smoke; no provider draw has been attempted
in this package. Hosted decision conformance remains unavailable locally and
was not dispatched.

## same-task-continuity

Keep inference as the sole staffing and hiring authority. The repair recognizes
only closed package history and performs no inference. Never rewrite the
malformed historical version in place: advance it through new immutable v2
lineage while preserving its evidence and accepted outcomes.

## next-bounded-work-package

Publish the clean repair branch, open a non-draft follow-up PR to exact main,
verify the remote head and `CLEAN` rollup, and merge with `[skip ci]` without
dispatching Actions. Then install only the resulting exact main into Claude,
Codex, ZCode, and the dashboard. Run provider smoke only after installation and
authentication boundaries are rechecked.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <named-fast-production-spine> -q -W error
python -m pytest tests/test_known_contractor_install.py \
  tests/test_contractor_version_identity.py tests/test_native_installer.py \
  tests/test_roster_bulk_seed.py tests/test_workforce_lifecycle.py \
  tests/test_workforce_hiring_contract.py tests/test_workforce_dynamic_hiring.py \
  tests/test_workforce_selection_safety.py -q -W error
node --test tests/dashboard_ui.test.mjs
python -m agency_runtime.cli eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
git diff --check
~~~

The complete 14-gate local harness and routing evaluation pass. Linux-only
behavior, integration coverage shards, and the decision-conformance mutation
phase remain unrun; no hosted workflow was dispatched.

## constraints

- Do not run the real Store migration from this unmerged evidence branch. It
  was proven only on a disposable transactionally backed-up copy.
- Claude's managed bundle is at exact main `da851c65`; Codex, ZCode, and the
  dashboard still point at the previous installed source until repaired main
  exists. The Store remains package v1.
- Hosted CI is not authorized or needed for this local gate package. Claude
  authentication requires operator action before its live smoke.
- OpenClaw and Hermes remain explicitly deferred to the later Linux handoff.
- Do not mutate or clean the primary checkout or unrelated worktrees.
- Do not change provider routing, Option A pins, AR-119 matrix cells, or
  previously consumed live evidence.
- Do not carry recruiter-only closest-worker or selection-evaluation prose into
  native child context.
