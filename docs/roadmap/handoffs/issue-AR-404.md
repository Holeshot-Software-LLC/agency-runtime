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
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar138-oldest-first-reconciliation
evidence_commit: fa4d042bf0260db4fd6c4ec16606740f5c3a7847
minimum_ledger_commit: 6bc9ccb0b0974b57abc79c518ccab7a982da0fff
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed September 6: oldest first, one record/PR/merge, then next; no
routine approval stops. Windows stays with the owner. AR-131 is done and PR
#698 merged at ac1ce173 (September 7, 04:12:09Z). AR-135 retention merged in
PR #699 at e2f7a5f2; local main is clean there. Merge ledger bcaddc1b starts the
owned AR-138 branch.

Current package: AR-138, live_demo complete and isolated acceptance pending. Existing coherence/mobile fixes
remain; actual browser review found contrast, keyboard-scroll/semantic and
desktop metric-clipping defects. Small HTML/CSS fixes and four regressions are
are checkpointed at d7231df3/7892096d. Final view-loaded browser receipt passes
21 checks at three widths, including 375 px. First isolated review satisfies
criteria 2–6 but contradicts 1: a replaced full refresh's late non-abort error
can mark newer healthy connection state Unavailable. Preserve the first review,
add failing regressions, then guard stale failure paths and reverify.

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
- Current count: 40 actual open trackers plus 98 unfinished legacy records,
  138 local unfinished. AR-135 retention changes no count. No duplicate tracker.
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
- AR-138: four focused regressions pass after red checks; dashboard Python
  modules 180 pass (28.80s), named spine 1085/three skips (69.50s). Initial
  repaired-wheel structural QA passes 21 view/viewport cases with zero axe
  violations and no unexpected console/HTTP errors. Real control failure keeps
  the last revision, shows a safe correlated UUID and recovers after restoration.
  All ten packaged dashboard assets match source. Final receipt at
  acceptance/evidence/AR-138-browser-20260907/report.json awaits view-scoped
  reads and requires a real control poll. Twenty-one checks pass; UI 142 pass,
  coverage 96.92/86.62/95.71 meets the actual 95/86/93 floors. Routing passes.

## Exact blocker

AR-138 has a concrete stale-error race to repair before acceptance or merge;
it remains open. AR-135 native proof is waiting_for_operator: one attended installed ZCode Agent
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

1. Final AR-138 evidence is committed at fa4d042b, ledger 6bc9ccb0. The isolated
   candidate is pinned to fa4d042b. Preserve its first isolated review before
   changing evidence; criteria 2–6 pass and criterion 1 contradicts.
2. Repair stale failures in full/control polling with generation guards and
   deferred-error regressions. Rebuild the wheel, rerun affected/browser checks,
   then freeze a repaired candidate for the second isolated acceptance pass.
3. If satisfied, update the legacy count, open one PR and merge normally.
   Review AR-140 next; AR-139 is already retired. Windows stays excluded.
4. AR-135 later retains its attended installed Agent/record-zero/full-Stop plan;
   it does not block an independent backlog disposition.

## Verification

Run metadata, policy availability, exact worklog, strict docs/tracker and diff
checks per package, with focused checks for touched behavior. AR-138 changes
only dashboard HTML/CSS plus optional QA tooling/tests. Run the current UI
coverage command with 95/86/93 floors and source inclusion; the mistakenly
used historical 95/90/96 command failed, not a current CI regression.
No new exhaustive corpus,
coverage/interpreter matrix, hosted dispatch or release/installed-live proof.
The graphify graph is absent; bounded source inspection was used, with no
graph build, specialist selection or native subagent staffing.

## Constraints

No credential creation, human-trust bypass, unmanaged gateway restart or provider
policy change. Runtime-requested Codex refreshes returned exit 1 with
registered files but activation required, trust unverified and mixed installed
projections. Do not retry or replace OpenClaw as part of backlog record cleanup.
Generated smoke and staged files do not establish normal-session activation.
