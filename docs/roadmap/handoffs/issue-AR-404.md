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
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-150-coordinate-dashboard-refresh-epochs.md
  - docs/roadmap/issue-AR-151-align-route-lab-host-eligibility.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar153-oldest-first-reconciliation
evidence_commit: ea57728532d99b5da0da60c7c6cec4dfa340fdba
minimum_ledger_commit: e6c3dba1c3897045cf7f17e374120ca82555e710
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 oldest-first backlog completion handoff

## Checkpoint

Owner resumed September 6: oldest first, one record/PR/merge, then next; no
routine approval stops. Windows stays with the owner. AR-131 is done and PR
#698 merged at ac1ce173 (September 7, 04:12:09Z). AR-135 retention merged in
PR #699 at e2f7a5f2. AR-138 merged through PR #700 at 1ada216c on September 7,
05:28:53Z. AR-140 retention merged in PR #701 at 7afa4b4d, 05:44:10Z;
AR-145 retirement merged in PR #702 at cd061668, 05:53:46Z. AR-150's four
criteria satisfy at ae71761f; PR #703 merged at 460f319b, 06:18:49Z. AR-151's
four revised criteria satisfy at 791820bb; PR #704 merged at 5a12f357, 06:46:57Z.
Main is clean there; merge ledger 26f3556b starts AR-153. AR-147 stays with owner.

Current AR-153: worker-filter-before-limit and bounded lineage already exist.
Exact totals/truncation share a Store read snapshot; HTTP caps detail at 200
rows/collection and 2 MiB, omitting history documents. The UI renders loaded
records and truthful totals. Fresh worker-detail Store/HTTP six pass (2.71s),
full workforce lifecycle 25 pass (8.08s), UI 176 pass (223.89ms), production
coverage 96.93/86.70/95.71. Product/tests/scripts equal 99e05d1f: explicitly reuse
its 274 dashboard/1085-spine results. No product or test change needed.
ADR-0105 replaces only the stale mandatory-full-corpus criterion with the named
bounded gate; original wording is retained. Candidate ea577285 is frozen for review.

## Completed evidence

- Exact earlier sequential dispositions are in the oldest-first ledger:
  AR-115/127 retired; AR-119/120/125/129/130 retained with genuine gaps.
- AR-151: 13 direct UI-to-POST cases pass. Nine reproduced dashboard fixtures
  repaired without runtime changes; full dashboard 274 pass (52.54s), named
  spine 1085/three skips (68.98s). ADR-0225 reconciles per-host ambiguity;
  first contradicted verdict remains at f954d1e9, all four revised criteria pass.
- AR-131 original MCP repairs were present. Its first isolated review exposed
  public identifier aliasing; first verdicts are preserved at 6a139e23.
  Repair 973acdb9 rejects lossy public IDs before Store writes while preserving
  internal native normalization. All six original criteria independently pass.
- AR-131: 13 new public-entry cases pass; MCP/CLI 126/five existing skips;
  named spine 1085/three skips (68.60s); UI 138; routing/Ruff pass; conformance
  184/184 protected mutations killed, zero survived/invalid, source unchanged.
  Broader 380-pass/one-failure/eight-skip run is not green: the unchanged
  fallback-roster fixture also fails on prior main and belongs to AR-176.
- Current count: 40 actual open trackers plus 94 unfinished legacy records,
  134 local unfinished after AR-151 completion. No duplicate tracker.
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
- AR-145: current source 7afa4b4d, coverage.py 7.15.0, branch instrumentation;
  41 focused observation/ownership/synthetic-report/authority cases pass in
  12.08s. No aggregate report, floor change or full-corpus claim. AR-176 owns
  real fixture/gap follow-up; AR-156 owns the release checklist's stale UI
  coverage command under the already-accepted ADR-0220 source/floor contract.

## Exact blocker

AR-153: current implementation verified; four isolated acceptance checks remain.
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

1. Obtain four isolated verdicts against frozen AR-153 candidate ea577285 before
   any completion/count change; preserve ADR-0105's explicit gate reconciliation.
2. Complete documentation/tracker checks and merge one AR-153 PR normally.
   Read back the actual merged head; update clean main by fast-forward only.
3. Start an owned AR-154 worktree and record the prior merge. AR-152 is done;
   Windows-only AR-147 stays with the owner and is not closed.
4. AR-135 retains its attended installed Agent/record-zero/full-Stop plan;
   it does not block an independent backlog disposition.

## Verification

Run metadata, policy availability, exact worklog, strict docs/tracker and diff
checks per package, with focused checks for touched behavior. AR-153 is docs-only.
Product/tests/scripts equal 99e05d1f; reuse its named spine and dashboard receipt
explicitly. New worker-detail/lifecycle/UI checks pass. Product/scripts equal
accepted AR-138 2ecde1a5; wheel/conformance reuse is same-byte, not a new run.
No exhaustive corpus, matrix,
hosted dispatch or release/installed-live proof.
The graphify graph is absent; bounded source inspection was used, with no
graph build, specialist selection or native subagent staffing.

## Constraints

No credential creation, human-trust bypass, unmanaged gateway restart or provider
policy change. Runtime-requested Codex refreshes returned exit 1 with
registered files but activation required, trust unverified and mixed installed
projections. Do not retry or replace OpenClaw as part of backlog record cleanup.
Generated smoke and staged files do not establish normal-session activation.
