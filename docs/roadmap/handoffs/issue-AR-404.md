---
title: "AR-404 oldest-first backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-07
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/acceptance/evidence/AR-170-response-correlation-20260907.md
  - docs/roadmap/issue-AR-168-rebuild-canonical-sdist-source-manifest.md
  - docs/roadmap/acceptance/evidence/AR-168-source-manifest-20260907.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-404-count-reconciliation-20260905.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar170-oldest-first-reconciliation
evidence_commit: 91273e4128b2a8bc666edd8fcf6023c534a5d55e
minimum_ledger_commit: d74585bdb0b142547fe0c9c758323f834cf89a89
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner continues one oldest record, one PR, normal merge, then next. Native
Windows remains with the owner. AR-166's six current criteria satisfy at
4a244776 after one citation-only recheck; first verdicts remain at bc28bf66.
PR #717 merged c6252499 at 11:36:32Z September 7. Clean main was fast-forwarded
before AR-168; 6363a788 records that merge. AR-168 retention merged in PR #718
at 790a01d7, 11:49:53Z September 7. Clean main was fast-forwarded before this
AR-170 tree; 00b14d02 records the merge. AR-167/169 are already retired.

## Completed evidence

AR-170 repairs three reproduced gaps. UI 193/current floors, fresh spine
1085/three skips (67.63s), four packaging/actual asset checks and Ruff 766 pass.
Present null IDs reject, exact lookup cannot page into another worker, and
pure validation errors retain sent IDs. Server/broker scope is unchanged.
Initial browser: 16 desktop passes, zero POSTs/errors before deliberate
injection, then wrong notice expectation times out. That report is preserved at
90654955; the corrected exact-source browser passes all 34 desktop/mobile checks,
zero POSTs. ADR-0230 reconciles only 6/7/9, preserving original wording.
Backend broker/lookup 18 pass. First isolated review is preserved at 662eb947:
1–6/9 satisfied, 7/8 absent for missing primary-report/source-identity excerpts.
Raw JSON, exact tree equivalence and fresh UI stdout supply those missing
artifacts. Second/final pass at 91273e41 satisfies 1/2/4/5/6/7/8; 3/9 remain
absent for complete collection-call-site and raw gate-receipt evidence.

AR-168 needs no generic manifest implementation change. Canonicalization
rebuilds from unique validated members; verification independently derives
membership and exact bytes. The removed-helper license trigger is historical,
but generic normalization and actual cross-OS proof remain relevant.

- Fresh focused packaging: 308 pass, one native-Windows deselection, 33.83s.
- Clean 6363a788 Linux wheel/source pair: independent portable verification and
  strict Twine pass. Exact hashes are in the committed source-manifest receipt.
- Source: 2,258 files, 2,256 unique manifest rows, self row present, root
  PKG-INFO/setup.cfg excluded, no CR/trailing newline.
- No runtime/test/script/workflow delta from accepted AR-166 4a244776.
  Its 1085/three-skip spine, UI 190 and scoped browser receipts are reused.
- Queue remains 40 actual trackers plus 84 legacy, 124 local unfinished.

## Exact blocker

AR-170 retains 3/9 evidence gaps at 91273e41. Two passes are complete; no third
review in this delivery. The issue records the next bounded evidence package.
Source/browser repairs and explicit existing-authority reconciliation are done.

AR-168 remains in_progress with its five original criteria/states unchanged.
Criterion 4 needs actual native Windows/Linux complete source equality at one
clean candidate; it is owner platform work also required by AR-160/ADR-0219.
Linux synthetic fixtures and an old Windows observation cannot supply it.
This retention does not certify a new installed artifact, release set or host.

Other retained holds: AR-159 hosted enforcement/check-app/bypass; AR-160
Windows/paired release/live publication; AR-156 Windows/profile and hosted
topology; AR-135 attended ZCode; AR-140 supported-runner performance;
AR-129/130/147 native Windows; AR-119/125 five-host/matched-value evidence.
AR-176 keeps six stale fixtures; AR-151's nine and AR-157's two repairs are done.
Ordinary-session unverified Agency/header behavior remains open.

## Same-task continuity

Own one worktree per record; never stage others' work or commit to main.
Every substantive commit gets an immediate narrow docs(worklog) ledger.
At 50 percent ensure a clean checkpoint, then continue the same task.
No empty commits, staffing or restart. Preserve first verdicts before corrections.

## Next bounded work package

1. Commit AR-170's final verdicts/retention and immediate ledger.
2. Publish the tested repair with exact remaining evidence gaps; no done flip.
3. Publish one normal PR/merge/readback, then AR-171. No native Windows work.

## Verification

Fresh UI/current coverage, named spine, source browser and actual asset checks.
Metadata/policy, exact worklog, strict docs/tracker, Ruff and diff checks.
No exhaustive corpus/coverage/matrix dispatch or native Windows. AR-165's
184/184 curated decision receipt is earlier Python evidence, not a new run.

## Constraints

No credentials, trust bypass or provider-policy changes. A fresh explicit
stale-hook directive was followed once: refresh exits 1, activation required,
hook trust unverified, mixed installed projections. No unattended retry absent
a new directive. Do not replace OpenClaw or claim normal-session activation.
