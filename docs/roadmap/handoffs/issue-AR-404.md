---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
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
branch: codex/ar165-oldest-first-reconciliation
evidence_commit: 220c0776e47c7b51d19010e2fd6ebdb92fd195a5
minimum_ledger_commit: 220c0776e47c7b51d19010e2fd6ebdb92fd195a5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next; no routine
approval pauses. Native Windows remains with the owner. AR-164 is complete:
all seven current criteria satisfy at 2a7c20c5; first review remains at 6ac3b1aa.
PR #715 merged ba6e55cb at 10:23:29Z September 7. Main was clean before this
AR-165 tree; 220c0776 records publication. AR-163/162 are already merged.

AR-165 has a real malformed-input gap: duplicate JSON keys can overwrite an
error or repository identity; object/non-finite HTTP-200 data can report
availability. Strict bounded UTF-8 parsing and array-of-objects success now
reject these inputs without changing either permitted workflow path.
The evidence commit above is the clean baseline; the repair candidate is being
prepared for its first isolated review.

## Completed evidence

- Four actual baseline false classifications now return exit 1 with no outputs.
- Twenty-five new cases; dependency focus 62 pass/128 deselected, 1.43s.
- Full non-Windows workflow package 235 pass/five deselected, 6.62s.
- Fresh named spine 1085 pass/three existing skips, 70.97s. Ruff 766 files pass.
- Parsed baseline/current workflow comparison: only classifier step differs;
  native action SHA/moderate threshold, probes, fallback and aggregate identical.
- Read-only identity is public/non-fork; exact comparison returns an empty array.
  This is calling-identity access, not current hosted CI or billing evidence.
- ADR-0228 explicitly reconciles only criteria 8/9 before review: any savings
  claim needs matched hosted evidence; AR-347's governed legacy exemption applies.
  All original wording remains; no savings claim or new tracker.
- Counts remain 40 actual trackers plus 86 legacy, 126 local unfinished.

## Exact blocker

AR-165's nine current criteria await candidate-bound isolated verdicts.
Do not mark done before all satisfy. The builder is evidence only.
Native action/fallback policy is unchanged; optional permissions projection was
already removed in 55a00db2 and must not be restored as an authority requirement.

AR-159 retains hosted enforcement/check-app/bypass proof; old billing cause is
not freshly established. AR-160 retains owner Windows/current paired artifact/
live release proof; Linux pair and generated host smokes are not native activation.
AR-156 retains Windows/profile and hosted topology proof; four Windows-profile
assumptions fail unchanged Linux main. AR-135 needs attended ZCode proof;
AR-140 retains supported-runner performance. AR-129/130/147 stay with the owner.
AR-119/125 retain five-host/matched-value proof. AR-176 has six separately
recorded stale fixtures; the AR-151 and AR-157 fixture repairs are not pending.
Ordinary-session unverified Agency/header remains open.

## Same-task continuity

Own one worktree/branch per record. Never commit to main or stage others' work.
Every substantive commit gets its immediate narrow docs(worklog) ledger.
At 50 percent make a clean substantive/ledger checkpoint, then continue the same
task. No empty commits, restart or staffing.

## Next bounded work package

1. Commit AR-165 repair/evidence and its immediate ledger; freeze exact candidate.
2. Run isolated nine-criterion review, complete only if all satisfy, then one
   normal PR/merge/readback. Preserve any first verdicts before corrections.
3. After that merge, continue to AR-166 in its own worktree.

## Verification

Run metadata/policy, exact worklog, strict docs/tracker, Ruff and diff checks.
No exhaustive corpus/coverage/matrix, dispatch, Windows or native host canary.
Graphify absent; no graph build or staffing. Source-identical DOM/browser
receipts are explicit reuse, not new runs.

## Constraints

No credentials, trust bypass, unmanaged restart or provider-policy changes.
Latest explicit Codex refresh again returned exit 1: activation required, hook
trust unverified, mixed installed projections. Do not retry unattended absent
a fresh explicit directive or replace OpenClaw. Registration is not session proof.
