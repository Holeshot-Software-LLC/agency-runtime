---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/roadmap/acceptance/evidence/AR-162-record-reconciliation-20260907.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar162-oldest-first-reconciliation
evidence_commit: d30b8ae0f4f339d17c28b35f24d95e4474aa3bed
minimum_ledger_commit: 6420e4a4a8914fb074869c9fed770d966cd1d570
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next; no routine
approval pauses. Native Windows remains with the owner. AR-160 remains retained;
PR #712 merged f18b5acf at 09:07:33Z September 7. Clean main was fast-forwarded
before this AR-162 tree; f0fc06de records publication.

AR-162's one-preflight topology exists. The actual baseline shell accepted HTTP
200 with no body, publishing available=true. The repaired classifier enforces
a 1 MiB transfer/read budget, strict JSON and alert-array shape, known visibility,
and only recognized private/internal unavailable messages. It publishes nothing
on invalid input. Request count, events, analyzers, permissions and aggregate
remain unchanged. Source changes only in codeql.yml and test_release_packaging.py.

## Completed evidence

- Whole-shell missing-body reproduction: baseline exit zero/available=true;
  repair exit one, empty stdout, bounded invalid-JSON diagnostic.
- CodeQL focus: 65 pass/100 deselected, 1.48s. Final full non-Windows workflow:
  210 pass/five deselected, 5.87s. No failures, new skips or suppression.
- Fresh warning-strict named spine: 1085 pass/three existing skips, 68.09s.
  Unchanged UI 188/browser 21 receipts reused, not rerun.
- Read-only identity: public/non-fork; owner-authenticated code-scanning endpoint
  returns HTTP 200/one-element array. Not workflow-token or hosted analyzer proof.
- ADR-0226 retains claim-conditional matched cost proof for 8 and explicitly
  reconciles 9 to AR-347's existing pre-tracker exemption after the first review.
  Criteria 1–7 remain unchanged; both original wordings and first verdicts remain.
- Exact pre-fan-out/repaired event and concurrency projections compare identical.
  Second evidence is documentation-only; workflow, tests and runtime equal fcdcd6eb.
  Strict docs pass 1174 Markdown files and tracker parity passes 397 mapped items.
- Counts remain 40 actual open trackers plus 89 unfinished legacy records,
  129 local unfinished. No duplicate tracker or completion claim.

## Exact blocker

First review c456b6bd is preserved: 1–6 and 8 satisfy, 7/9 are absent. The new
receipt supplies historical comparison and ADR-0226 explicitly adopts AR-347's
tracker rule. The second record is frozen at d30b8ae0 with ledger 6420e4a4;
all nine need new verdicts. No implementation failure or closure is inferred.

AR-159 retains hosted enforcement/check-app/bypass proof; main is unprotected
with no current checks. Old billing cause is not freshly established; the extra
dynamic CodeQL identity remains a check-binding question, not authority to alter it.
AR-160 retains owner Windows and current paired artifact/live release proof.

AR-156 retains owner Windows/profile and hosted topology proof; all thirteen
criteria remain. Its four Windows-profile assumptions fail unchanged Linux
main. AR-135 needs attended ZCode Agent/record-zero/full Stop proof. AR-140
retains supported-runner performance including Windows. AR-129/130/147 stay
with the owner; AR-119/125 retain five-host and matched-value proof. AR-176 keeps
six separately recorded stale fixtures; AR-151's nine dashboard and AR-157's
two HTTP repairs are not pending. Ordinary-session unverified Agency/header
remains unfinished.

## Same-task continuity

Own one worktree/branch per record. Never commit to main or stage others' work.
Each substantive commit gets its immediately following narrow docs(worklog)
ledger; record the prior merge in the next tree. At 50 percent ensure a clean
checkpoint, then continue the same task. No empty commits, restart or staffing.

## Next bounded work package

1. Commit AR-162's second candidate freeze and immediate ledger.
2. Run all nine isolated checks once at d30b8ae0.
3. On accepted completion, reconcile counts and publish one normal PR, then
   proceed to the next oldest unfinished non-Windows record.

## Verification

Run metadata/policy, exact worklog, strict docs/tracker, Ruff and diff checks.
No exhaustive corpus/coverage/matrix, dispatch, Windows or native host canary.
At <=50 percent finish this smallest clean substantive/ledger checkpoint and
continue in the same task. Graphify absent; no graph build or staffing.

## Constraints

No credential creation, trust bypass, unmanaged restart or provider-policy
change. The newly requested Codex refresh again returned exit 1: activation
required, hook trust unverified, mixed installed projections. Do not retry
unattended or replace OpenClaw. Registration is not normal-session proof.
