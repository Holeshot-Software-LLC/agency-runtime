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
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/acceptance/issue-AR-131.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar140-oldest-first-reconciliation
evidence_commit: 1ada216c208777630ec7162acf5a390f420fc0a4
minimum_ledger_commit: 82fb202882fe973d9120d070eb64db66d29ecc86
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed September 6: oldest first, one record/PR/merge, then next; no
routine approval stops. Windows stays with the owner. AR-131 is done and PR
#698 merged at ac1ce173 (September 7, 04:12:09Z). AR-135 retention merged in
PR #699 at e2f7a5f2. AR-138 merged through PR #700 at 1ada216c on September 7,
05:28:53Z; local main is clean there. Merge ledger 82fb2028 starts AR-140.

Current package: AR-140 retained. Optimization and budgets are implemented;
all 39 local Linux routing/performance gates and 202 focused tests pass. No
code/threshold change. ADR-0121 governs recall/synthetic-cache evidence; AR-253
owns staffing latency. Preserve AR-140's isolated supported-runner requirement,
with the Windows arm left to the owner. Publish one disposition PR, then AR-145.

## Completed evidence

- Exact earlier sequential dispositions are in the oldest-first ledger:
  AR-115/127 retired; AR-119/120/125/129/130 retained with genuine gaps.
- AR-131 original MCP repairs were present. Its first isolated review exposed
  public identifier aliasing; first verdicts are preserved at 6a139e23.
  Repair 973acdb9 rejects lossy public IDs before Store writes while preserving
  internal native normalization. All six original criteria independently pass.
- AR-131: 13 new public-entry cases pass; MCP/CLI 126/five existing skips;
  named spine 1085/three skips (68.60s); UI 138; routing/Ruff pass; conformance
  184/184 protected mutations killed, zero survived/invalid, source unchanged.
  Broader 380-pass/one-failure/eight-skip run is not green: the unchanged
  fallback-roster fixture also fails on prior main and belongs to AR-176.
- Current count: 40 actual open trackers plus 97 unfinished legacy records,
  137 local unfinished after AR-138 acceptance. No duplicate tracker.
- AR-135 source: independent ZCode renderer/config registration, exact seven
  hooks, idempotency, preservation, toggle/rollback/drift and host identity exist.
  Current tests: 16 installer/header (4.74s), 13 selected hook/Stop (5.80s),
  four child-adapter/delivery/profile cases (0.31s), all pass.
- Current-source generated ZCode smoke: 4/4 pass, no skips. It proves Store,
  roster, five-host parity and isolated ZCode config/process contracts:
  preservation, idempotency, per-handler toggles and SessionStart execution.
  It does not launch the native ZCode app, parent/child or full Stop lifecycle.
- Read-only ZCode inspection: discovered/staged/registered/enabled true, loaded
  unknown, no canary/attestation, enabled-runtime-unverified. Executable null;
  command lookup also finds no zcode CLI. August 19 record-zero evidence stays
  historical, not current-package certification.
- AR-138: dashboard Python 180 pass (28.80s), repeated named spine 1085/three
  existing skips (99.40s). UI 172 pass; coverage 96.93/86.58/95.71 meets the
  unchanged 95/86/93 floors. Routing passes. The first-candidate conformance
  run kills 184/184, zero survived/invalid, source unchanged; no Python decision
  implementation or selected test changed in the subsequent JavaScript repair.
- Final browser receipt: acceptance/evidence/AR-138-browser-repaired-20260907/
  report.json, observed 05:15:13Z September 7. Twenty-one loaded views at
  1280/1024/375 px pass, zero axe violations/overflow/clipping or unexpected
  console/HTTP errors. Real polls preserve focus/selection/disclosures; injected
  control failure retains the revision, shows a correlated safe ID and recovers.
  All ten wheel assets match source. Full WCAG/screen-reader/native-host proof
  is not claimed. All six isolated second-pass verdicts are satisfied.
- AR-140: local Linux narrowing/cache p95 1.081/0.201 ms; fresh version-command
  median 16.989 ms; all three retrieval time/memory budgets pass. Exact report:
  acceptance/evidence/AR-140-linux-routing-20260907.json. Required recall and
  top-one relevance 1.0, precision at three 0.6364 above 0.60, forbidden zero.
  Focused 135 pass/two performance tests deselected, plus 67 pass; standalone
  complete evaluation supplies performance evidence. Not a staffing decision.

## Exact blocker

AR-140 retains isolated supported-runner proof, including the owner's Windows
arm. Local passing developer-host numbers do not waive that explicit criterion.
AR-135 native proof is waiting_for_operator: one attended installed ZCode Agent
success/failure and full parent Stop capture. Do not invent a headless backend
or promote a stubbed hook test into native proof. This does not block the next
independent backlog disposition.

AR-176 owns six stale fixture cases found in AR-127/130/131. Ordinary-session
unverified Agency staffing/header remains a separate unfinished concern.
AR-119/125 retain the wider five-host/value evidence; no matrix cell is waived.

## Same-task continuity

Use one owned worktree/branch per item; never commit directly to main.
Substantive commit then immediate narrow docs(worklog) ledger. Record the prior
merge in the next worktree. Preserve unrelated staged work in other trees.
At 50-percent context, ensure a clean evidence/ledger checkpoint and continue
the same task; do not spawn a replacement task or close an unfinished umbrella.

## Next bounded work package

1. Commit AR-140's current evidence and retained-record reconciliation, then its
   immediate exact ledger. No acceptance flip or duplicate tracker.
2. Complete documentation/tracker checks and merge one disposition PR normally.
   Read back the actual merged head; update clean main by fast-forward only.
3. Start an owned AR-145 worktree and record the prior merge. AR-141/142/144
   are done, AR-143 retired; Windows work remains excluded.
4. AR-135 retains its attended installed Agent/record-zero/full-Stop plan;
   it does not block an independent backlog disposition.

## Verification

Run metadata, policy availability, exact worklog, strict docs/tracker and diff
checks per package, with focused checks for touched behavior. AR-140 changes
only documentation/evidence. Git comparison proves product/tests/scripts equal
to accepted AR-138 candidate 2ecde1a5: reuse its named spine/UI/conformance with
that explicit scope, not a newly run claim. Current AR-140 focused/eval results
are recorded separately. No exhaustive corpus, coverage/interpreter matrix,
hosted dispatch or release/installed-live proof.
The graphify graph is absent; bounded source inspection was used, with no
graph build, specialist selection or native subagent staffing.

## Constraints

No credential creation, human-trust bypass, unmanaged gateway restart or provider
policy change. Runtime-requested Codex refreshes returned exit 1 with
registered files but activation required, trust unverified and mixed installed
projections. Do not retry or replace OpenClaw as part of backlog record cleanup.
Generated smoke and staged files do not establish normal-session activation.
