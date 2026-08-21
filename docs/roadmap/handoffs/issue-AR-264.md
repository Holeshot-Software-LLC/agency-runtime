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
branch: codex/ar264-contractor-execution-profile
evidence_commit: 3262858bd55e26cd0d938bc3298f04ed0694a70b
minimum_ledger_commit: 3262858bd55e26cd0d938bc3298f04ed0694a70b
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-264 active recovery capsule

## checkpoint

- Worktree `C:\Workspaces\Holeshot Software\agency-runtime-ar264` is on branch
  `codex/ar264-contractor-execution-profile`, two planning commits above exact
  remote main `0d8a2355` before this implementation checkpoint.
- The primary checkout has unrelated owner WIP and must not be touched.
- Context telemetry reported 9.0 percent remaining after the focused
  implementation slice, requiring this clean local recovery checkpoint.

## completed-evidence

- Employment-contract v2 and compiler v2 render five closed execution sections;
  live hiring refuses v1 while historical parser/compiler replay remains.
- All 15 known contractors carry reviewed profiles. TypeScript v2 is
  `contractor-2-6b0d5cae3b65a44d`; exact v1 remains
  `contractor-1-5e6a02cdaaf0bfde` with its prior full SHA-256 identity.
- Exact package-v1 -> package-v2 Store test preserves worker identity, advances
  revision 0 -> 1, retains the parent-linked v1 prompt, records package—not
  inference—event authority, and is idempotent.
- Dashboard API test projects `changed artifacts and focused verification
  results`; all 134 dashboard UI tests pass and no false evidence fallback is
  rendered for that worker.
- Focused contract/version/upgrade and hiring checks pass; widened startup,
  routing, CLI-config, and workforce lifecycle checks report 122 passed.
- A wider public/prompt compatibility diagnostic reported 124 passed, one
  expected skip, and one unrelated assertion that still expects the retired
  fallback pair even though the governed constant is empty.

## exact-blocker

No implementation blocker. Publication, tracker creation, installation, and
live inference are outside the current local authorization.

## same-task-continuity

Keep inference as the sole staffing and hiring authority. Do not add a raw
prompt field, another provider call, deterministic worker selection, or a
silent rewrite of historical prompt bytes. Preserve v1 evidence exactly and
advance packaged contractors only through governed lineage.

## next-bounded-work-package

Run the named fast Python spine, full Ruff/format, documentation validation,
dashboard UI gate, and routing/conformance evaluations. Fix only findings that
invalidate AR-264, then update evidence and create the substantive/ledger pair.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_hiring_contract.py tests/test_contractor_version_identity.py tests/test_known_contractor_install.py -q -W error
python -m pytest tests/test_workforce_dynamic_hiring.py tests/test_contractor_minting_host_parity.py -q -W error
python -m pytest tests/test_dashboard.py::test_dashboard_workforce_and_hiring_apis_share_revision_bound_lifecycle -q -W error
node --test tests/dashboard_ui.test.mjs
git diff --check
~~~

## constraints

- No push, PR, merge, tracker creation, installation, or live inference is
  authorized by this local implementation approval.
- Do not mutate or clean the primary checkout or unrelated worktrees.
- Do not change provider routing, Option A pins, AR-119 matrix cells, or
  previously consumed live evidence.
- Do not carry recruiter-only closest-worker or selection-evaluation prose into
  native child context.
