---
title: "AR-170 response correlation repair evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, dashboard, security, backlog]
related:
  - docs/decisions/0230-reconcile-response-correlation-with-owner-controls.md
  - docs/roadmap/acceptance/evidence/AR-170-browser-20260907/final/report.json
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/acceptance/evidence/AR-170-browser-20260907/report.json
  - docs/decisions/0117-unify-owner-control-authority.md
  - agency_runtime/dashboard/dashboard-core.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/dashboard/dashboard-live.js
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
---

# AR-170: Current response correlation evidence

## Reproductions and repair

Baseline: clean 00b14d02b7c3b3fbec6430e57798fbf3ec04039b after PR #718.
September 7 Linux / Node 22.23.2. Three new tests fail on original behavior:

- Explicit null request_id: missing expected rejection, 60.139922 ms.
  New test covers six JSON values with/without matching response headers
  (12 combinations), retaining only the generated ID in notices/logs.
- Worker validation: last-good detail survives but its notice lacks the sent ID.
  New test covers wrong slug, invalid revision and missing evidence.
- Exact lookup: a truncated first page allows a wrong-worker second page;
  expected rejection is missing. These latter two red cases take 62.368299 ms.

The helper filters absent headers separately from present body IDs. Optional
pure response validation runs inside its success/correlation boundary, wrapping
failures with the exact generated ID/status. Worker detail and exact lookup use
it before state commit. Lookup rejects truncation; the real server already
returns zero/one rows, false truncated and null cursor. General pagination,
stale-generation guards, server authentication and broker scope are unchanged.

## Fresh verification

UI: 193 pass, zero skips/failures, 194.986746 ms. Production-only coverage:
96.93 percent lines, 86.75 branches, 95.73 functions, passing unchanged
95/86/93 floors. Named spine: 1085 pass/three existing skips, 67.63s.
Dashboard/resource-addressability: four pass/186 deselected, 0.16s, including
the actual asset ceiling. Final assets are 387039 bytes, below unchanged
378 KiB. Three non-executable config comments removed; behavior unchanged.
Ruff check/format pass for 766 files.
Fresh backend broker/lookup cases: 18 pass, 156 deselected, 2.96s.

## Browser checkpoint

Private five-agent Store, source-served Chromium 152.0.7977.64, outbound
provider access denied, non-GET browser operations intercepted. Initial report
records 16 passing desktop checks: seven views, six tabs, no application console
errors, keyboard skip and owner controls surviving asynchronous refresh.
Zero POSTs. Hidden elements stay hidden; IDs/aria-controls are consistent;
headings/document fit 1280 pixels.

The injected-null check times out after 15s: its fixture expects raw API text,
but markControlStale deliberately shows retained-state text and the sent ID.
Correct only that expectation and retain the original report/screenshot.
Mobile/full revised sweep is not yet claimed. No installed-wheel, native-host,
human-presence, full WCAG or release-publication claim.

## Final browser sweep

At clean f1ff818c7a6752de8f11a1157b49473577b3ab65, all source fixes remain those
of 90654955. Corrected fixture passes 34 checks, 17 each at 1280x900 and
375x812: seven views, six evidence tabs, no application errors during the
ordinary sweep, keyboard skip navigation, owner controls after refresh and
rejection of a present null body ID despite a matching header. Each injected
failure deliberately produces one safe diagnostic; its notice contains the sent
UUID and retains configuration state. Zero POSTs; no owner profile is used.

All seven inspected source assets match served bytes. Core SHA-256:
62a2f817e8ff63e929969839cd29bb5b3695de654919b18ef1f53c8cab3799e1.
Full hashes, 34 checks and screenshots are in final/report.json, SHA-256
2b7f8531b44cbf14be0f1dde7bd1b036f4416a058e902eb8f388f717efce6a44.
The initial report remains alongside it; no source change or assertion weakening
followed the first run. The assertion now names the actual retained-state notice.
Screenshots were inspected; automated layout/hidden/ID checks cover every view.
No full accessibility certification, installed-wheel or native activation claim.

## Requirement reconciliation

ADR-0230 changes only criteria 6/7/9 before first review, under ADR-0117 and
ADR-0105. Original read-only/attended-only/final-release wording is preserved.
Response identity, last-good state and the seven-view/six-tab gate remain.

## Publication validation

The initial acceptance draft failed structural validation because its empty
Verification table header was missing. No isolated verifier ran. The table
schema is corrected before re-freezing. Current metadata/policy, worklog,
strict docs/tracker and diff checks now pass: 1196 Markdown files, 397 mapped
items and two historical PR exceptions. Ruff already passes.
No exhaustive corpus, four-shard coverage or matrix dispatch.
AR-165's earlier 184/184 curated decision receipt is reused for unchanged Python
production code; it is not a fresh JS mutation run.

Isolated review is next; no acceptance verdict is asserted by the builder.
Windows stays with the owner.
Counts remain 40 mapped plus 84 legacy = 124 unfinished.
