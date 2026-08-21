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
evidence_commit: 9b19bc1872431133d94c2810548fb1280a6445b9
minimum_ledger_commit: 9b19bc1872431133d94c2810548fb1280a6445b9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
---

# AR-264 active recovery capsule

## checkpoint

- Worktree `C:\Workspaces\Holeshot Software\agency-runtime-ar264` is on branch
  `codex/ar264-contractor-execution-profile`, eight clean published commits
  above exact remote main `0d8a2355` before this PR-receipt delta.
- The primary checkout has unrelated owner WIP and must not be touched.
- Context telemetry required the clean implementation checkpoint at 9.0 percent
  remaining. After normal compaction, the latest reading is 79.3 percent and
  permits the same task to continue.

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
- The governing named fast Python spine reports 806 passed and 20 skipped in
  135.09 seconds. Full Ruff and format checks pass across 682 files.
- Metadata checks cover 731 Markdown files, the policy projection and 1,079-row
  worklog are current, documentation validation passes, `git diff --check`
  passes, and the routing evaluation passes every correctness, safety,
  performance, and scale gate.
- GitHub issue #313 is open with the exact AR-264 title, canonical body, URL,
  and `epic:roster-governance` label. Repository-wide strict tracker checks
  still fail on pre-existing missing trackers and historical state/label debt;
  neither strict failure reports AR-264.
- GitHub PR #314 is open, non-draft, mergeable, targets `main`, has zero hosted
  status checks, and its remote head exactly matches the clean local branch.
- A wider public/prompt compatibility diagnostic reported 124 passed, one
  expected skip, and one unrelated assertion that still expects the retired
  fallback pair even though the governed constant is empty.

## exact-blocker

No implementation blocker. The decision-conformance mutation phase cannot run
locally according to `CONTRIBUTING.md`; this Codex Desktop session correctly
refused it because the host did not attest a private scratch capability. Hosted
CI was not dispatched. Tracker #313 and non-draft PR #314 are linked and
directly verified. Merge, installation, and live inference remain unauthorized.

## same-task-continuity

Keep inference as the sole staffing and hiring authority. Do not add a raw
prompt field, another provider call, deterministic worker selection, or a
silent rewrite of historical prompt bytes. Preserve v1 evidence exactly and
advance packaged contractors only through governed lineage.

## next-bounded-work-package

Record and push the PR publication receipt, then stop for owner review and
explicit merge authorization. Installation, live smoke testing, and hosted
decision conformance remain separately authorized operations.

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
node --test tests/dashboard_ui.test.mjs
python -m agency_runtime.cli eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
git diff --check
~~~

The decision-conformance command stopped before mutation execution with `Codex
host scratch was not attested by the host`; the contributor guide classifies
that mutation phase as hosted-only. All other commands above pass locally.

## constraints

- Tracker creation, branch push, and non-draft PR publication are complete.
  Merge, installation, hosted CI, and live inference remain unauthorized.
- Do not mutate or clean the primary checkout or unrelated worktrees.
- Do not change provider routing, Option A pins, AR-119 matrix cells, or
  previously consumed live evidence.
- Do not carry recruiter-only closest-worker or selection-evaluation prose into
  native child context.
