---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/acceptance/issue-AR-164.md
  - docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-163-reopen-stale-remediation-authority.md
  - docs/roadmap/acceptance/issue-AR-163.md
  - docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar164-oldest-first-reconciliation
evidence_commit: 083ae8b58378d97c139cfb79debf0a49175b3f92
minimum_ledger_commit: 635d7dc3c6733fd3706b387f1888f36e88a8ec19
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next; no routine
approval pauses. Native Windows remains with the owner. AR-163 is complete:
all eight original criteria satisfy at fd551fd4 without runtime/test changes.
PR #714 merged 6d1ca01f at 10:04:47Z September 7. Main was clean and fast-forwarded
before this AR-164 tree; 7e0dc5d9 records publication. AR-162 completion remains
merged in PR #713 with original wording and first review preserved.

AR-164's ancestor executable boundary already exists. No runtime/test gap was
found. The stale fifth criterion names deleted Agency-owned execution backends.
ADR-0227 explicitly maps it to current CLI-provider, installer, dashboard and
smoke launch paths, preserving original wording and all other criteria. Retired
worker backends stay removed; native hosts own worker execution.

## Completed evidence

- Discovery: 38 pass/one native Windows deselection, 0.14s. Sibling-bin poisoning,
  first Git selection, explicit/resolver rejection, links and safe external PATH.
- Current six-module launch package: 129 pass/23 Windows-named deselections,
  3.39s. Surviving Git/process package: 24 pass/three deselections, 0.63s.
  All warning-strict, no failures/skips; no new skips or xfails.
- Windows spelling/case/PATHEXT are portable Linux simulations, not native
  Windows, PowerShell, ACL or host-activation evidence.
- Product/test/script/config bytes match fcdcd6eb: reuse named spine 1085
  pass/three existing skips, 68.09s. Same-byte AR-163 DOM 188 passes reused.
  No redundant spine, browser or installation run is claimed.
- Counts remain 40 actual trackers plus 87 legacy, 127 local unfinished.

## Exact blocker

AR-164 first review at 083ae8b5 satisfies 1–4 and 6–7. Criterion 5 lacks an
actual candidate tree listing proving the described backend absence. Preserve
the first verdicts, then add exact Git output and freeze a new evidence candidate.
No implementation defect, additional requirement change or completion is inferred.

AR-159 retains hosted enforcement/check-app/bypass proof; main has no current
enforcement evidence. Old billing cause is not freshly established; the extra
dynamic CodeQL identity is a check-binding question, not authority to alter it.
AR-160 retains owner Windows/current paired artifact/live release proof; its
fresh Linux wheel/source and all generated five-host smokes passed, not native
activation. AR-156 retains Windows/profile and hosted topology evidence; its
four Windows-profile assumptions fail unchanged Linux main.

AR-135 needs attended ZCode Agent/record-zero/full Stop proof. AR-140 retains
supported-runner performance including Windows. AR-129/130/147 stay with the
owner; AR-119/125 retain five-host and matched-value proof. AR-176 keeps six
separately recorded stale fixtures; AR-151's nine dashboard and AR-157's two HTTP
repairs are not pending. Ordinary-session unverified Agency/header remains open.

## Same-task continuity

Own one worktree/branch per record. Never commit to main or stage others' work.
Each substantive commit gets an immediate narrow docs(worklog) ledger; record
the prior merge in the next tree. At 50 percent ensure a clean checkpoint, then
continue the same task. No empty commits, restart or staffing.

## Next bounded work package

1. Seven rowsets are frozen at 083ae8b5 with ledger 635d7dc3. Commit this freeze
   and its immediate ledger, then run isolated checks once.
2. If all satisfy, reconcile local completion/counts, publish one normal PR and
   read back the merge before starting the next record.
3. Next is AR-165's dependency-review capability boundary, in its own worktree.

## Verification

Run metadata/policy, exact worklog, strict docs/tracker, Ruff and diff checks.
No exhaustive corpus/coverage/matrix, dispatch, Windows or native host canary.
At <=50 percent finish the smallest clean substantive/ledger checkpoint and
continue in the same task. Graphify absent; no graph build or staffing.

## Constraints

No credentials, trust bypass, unmanaged restart or provider-policy changes.
The latest explicitly requested Codex refresh again returned exit 1: activation
required, hook trust unverified, mixed installed projections. Do not retry
unattended or replace OpenClaw. Registration is not normal-session proof.
