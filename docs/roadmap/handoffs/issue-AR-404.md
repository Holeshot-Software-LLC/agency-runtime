---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md
  - docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/acceptance/issue-AR-165.md
  - docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md
  - docs/decisions/0228-reconcile-dependency-review-evidence-gates.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar166-oldest-first-reconciliation
evidence_commit: 4a24477669e1b773b27626f2cd67631fbe78f875
minimum_ledger_commit: bd6e0f5c53212f5c74fa442f8757730f9f81864f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next. Native
Windows remains with the owner. AR-165 all nine criteria satisfy at 9effff3f;
PR #716 merged 520a10e3 at 10:58:51Z September 7. Main was clean before this
AR-166 tree; 44c94c92 records that merge. No next record before the current merge.

AR-166 retains truthful correlation/privacy requirements, but its first
criterion still mandates superseded read-only owner controls. ADR-0117 already
restored owner controls. The provider-secret selector incorrectly stayed
disabled for all valid providers. A one-line assignment repair and direct
interaction test restore owner choice without changing broker/backend authority.
ADR-0229 explicitly replaces only criterion 1 and preserves its original wording.

## Completed evidence

- Against baseline, two focused cases fail: expected enabled, actual disabled.
- Selector checkpoint UI: 189 pass; null-error correction UI: 190 pass,
  no skips/failures, 231.878074 ms.
  Current production coverage 96.93/86.71/95.71 passes unchanged 95/86/93 floors.
- Current backend/owner five-module package: 235 pass, 46.37s.
- Fresh named spine after both fixes: 1085 pass/three existing skips, 66.99s.
  Asset contracts three pass/187 deselected; Ruff 766 files pass.
- New test preserves second-provider choice through re-render, stages only its
  secret operation, retains key redaction, disables four invalid/empty states,
  and recovers after stale selection removal.
- The old 8192-character preview is historical; AR-298's complete bounded
  Store definition is at most 262144 characters and is not runtime proof.
- Queue stays 40 actual trackers plus 85 legacy, 125 local unfinished.

## Exact blocker

Both fixes pass 20 source-served browser checks at 1280/375 pixels, with zero
POSTs and exact served config/core hashes. This includes null-401 terminal
notices retaining safe IDs. The initial zero-check timeout is retained and
explained by the fixture's obsolete config endpoint. Six isolated verdicts
were reviewed at 4a244776. Criteria 1 and 3–6 satisfy; criterion 2 is absent
because reconciliation implementation/direct ID assertions were not supplied.
Preserve all first verdicts, inspect that exact path, then one bounded recheck.
No requirement or authority change follows from this evidence gap.

Retained holds: AR-159 hosted enforcement/check-app/bypass; AR-160 Windows/
paired release/live publication; AR-156 Windows/profile and hosted topology;
AR-135 attended ZCode; AR-140 supported-runner performance; AR-129/130/147
native Windows; AR-119/125 five-host/matched-value evidence. AR-176 keeps six
stale fixtures; AR-151's nine and AR-157's two repaired fixtures are not pending.
Ordinary-session unverified Agency/header behavior remains open.

## Same-task continuity

Own one worktree per record; never stage others' work or commit to main.
Every substantive commit gets an immediate narrow docs(worklog) ledger.
At 50 percent ensure a clean checkpoint, then continue the same task.
No empty commits, staffing or restart. Preserve first verdicts before corrections.

## Next bounded work package

1. Preserve the final browser/evidence candidate and immediate ledger.
2. Run the frozen six-check isolated review; complete only if all pass.
3. One PR/normal merge/readback, then AR-168 (AR-167 already retired).

## Verification

Focused tests, named spine, metadata/policy, exact worklog, strict docs/tracker,
Ruff and diff checks. No exhaustive corpus/coverage/matrix dispatch or native
Windows. AR-165's 184/184 curated decision check is earlier Python evidence,
not a fresh AR-166 run. Browser work must identify source vs installed scope.

## Constraints

No credentials, trust bypass or provider-policy changes. The latest explicitly
requested Codex refresh returns exit 1: activation required, hook trust unverified,
mixed installed projections. No unattended retry absent a fresh directive.
Do not replace OpenClaw or present registration as normal-session activation.
