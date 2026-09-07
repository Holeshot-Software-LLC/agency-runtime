---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-171-redact-dashboard-lifecycle-reasons.md
  - docs/roadmap/acceptance/issue-AR-171.md
  - docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/acceptance/issue-AR-170.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar171-oldest-first-reconciliation
evidence_commit: 8a8db2aeeae788829ae7dfc641142d7c04376e6e
minimum_ledger_commit: dc19f1f8d512e71203f1aa7507504d14a988cf48
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next. Native
Windows remains with the owner. PR #719 merged AR-170's three tested response
repairs at 29e76943, 12:18:00Z September 7. Main was clean and fast-forwarded
before the separate AR-171 tree; 05d7696a records that merge.

## Completed evidence

AR-171's privacy repair is present: reduced Store event metadata excludes raw
reason, event document and reason-derived hashes, returning a bool. Full owner
history retains the governed originals. HTTP explicitly selects reduced mode;
production rendering uses only primitive true and fixed Reason recorded text.

- New eight-value DOM test includes hostile note/HTML/hash/evidence fields;
  no raw content, hash or IMG node renders.
- Complete Store/workforce and real loopback HTTP: 199 pass, 48.66s.
- UI 194 pass, zero skips/failures; 96.93/86.77/95.73 meets unchanged floors.
- Fresh named spine: 1085 pass/three existing skips, 67.57s.
- Metadata/policy/worklog, strict docs/tracker, Ruff and diff pass.
  Raw transcripts are committed with the packet, not just summaries.
- No runtime/script/workflow change. Only criterion 6 is reconciled under
  ADR-0105; original wording and first five criteria remain.
- All six criteria satisfy in the first isolated review at 8a8db2ae.
- Queue becomes 40 actual trackers plus 83 legacy, 123 unfinished.

## Exact blocker

AR-171 has no scoped acceptance blocker. All six isolated verdicts satisfy;
commit completion and its ledger, publish one normal PR, merge and read back.

AR-170 remains in_progress: first review at 662eb947 and final candidate
91273e41 are preserved. Final 1/2/4/5/6/7/8 satisfy, 3/9 need complete collection
call sites and raw gate receipts. Two-pass limit reached; no third review.
Its 34-check browser proof and three tested code repairs are on main.

Other holds: AR-168/160 same-candidate native Windows/paired artifact proof;
AR-159 hosted enforcement/check-app/bypass; AR-156 Windows/profile and hosted
topology; AR-135 attended ZCode; AR-140 supported-runner performance;
AR-129/130/147 native Windows; AR-119/125 five-host/matched-value evidence.
AR-176 keeps six stale fixtures; AR-151's nine and AR-157's two are repaired.
Ordinary-session unverified Agency/header behavior remains open.

## Same-task continuity

Own one worktree per record; never stage others' work or commit to main.
Each substantive commit gets an immediate narrow docs(worklog) ledger.
At 50 percent ensure a clean checkpoint and continue the same task.
No empty commits, staffing or restart. Preserve verdicts before corrections.

## Next bounded work package

1. Commit AR-171's accepted completion and immediate ledger.
2. Publish its normal PR; no acceptance rerun.
3. Publish one normal PR/merge/readback, then AR-172. No native Windows work.

## Verification

Fresh Store/HTTP, UI/current coverage, named spine and strict documentation
checks with raw output. No exhaustive corpus/coverage/matrix dispatch.
AR-165's 184/184 curated decision receipt is earlier unchanged Python evidence,
not a fresh run or a new JS mutation evaluation.

## Constraints

No credentials, trust bypass or provider-policy changes. The last fresh
stale-hook directive was followed once: refresh exits 1, activation required,
hook trust unverified and mixed installed projections. No retry absent a new
directive. Do not replace OpenClaw or claim normal-session activation.
