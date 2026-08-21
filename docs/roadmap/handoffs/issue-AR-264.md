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
evidence_commit: 0d8a23551b6e562a71fca0a3c8f67d29c92da3ce
minimum_ledger_commit: 0d8a23551b6e562a71fca0a3c8f67d29c92da3ce
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-264 active recovery capsule

## checkpoint

- Worktree `C:\Workspaces\Holeshot Software\agency-runtime-ar264` is on clean
  branch `codex/ar264-contractor-execution-profile` from exact remote main
  `0d8a2355`.
- The primary checkout has unrelated owner WIP and must not be touched.
- Context telemetry reported 38.2 percent remaining. Exact main is the reused
  clean checkpoint before this bounded planning slice.

## completed-evidence

- Source inspection proves the native child receives the exact work unit and
  immutable specialist prompt as separate integrity-bound inputs.
- Hiring inference already returns closed structured data and is explicitly
  forbidden from writing executable instructions.
- Contractor template v1 embeds dense contract JSON, including recruiter-only
  comparisons and evaluations, and has no role-specific execution method.
- Packaged revision metadata contains `evidence_requirements`; workforce
  contract v2 does not, but the dashboard reads the missing workforce field.
- ADR-0162 fixes the boundary: structured execution data, compiler-owned prompt
  syntax, exact v1 replay, immutable packaged revision advance.

## exact-blocker

No implementation blocker. Publication, tracker creation, installation, and
live inference are outside the current local authorization.

## same-task-continuity

Keep inference as the sole staffing and hiring authority. Do not add a raw
prompt field, another provider call, deterministic worker selection, or a
silent rewrite of historical prompt bytes. Preserve v1 evidence exactly and
advance packaged contractors only through governed lineage.

## next-bounded-work-package

Implement the closed v2 execution profile and compiler with exact v1
compatibility. Add package-owned immutable version advance. Then repair the
dashboard evidence projection from revision metadata and run focused tests.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_hiring_contract.py tests/test_contractor_version_identity.py -q -W error
python -m pytest tests/test_workforce_dynamic_hiring.py tests/test_workforce_hiring.py -q -W error
python -m pytest tests/test_dashboard.py -q -W error
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
