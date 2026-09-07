---
title: "AR-170 response correlation repair evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, dashboard, security, backlog]
related:
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

## Pending scope

Explicitly reconcile stale read-only/attended-only and exhaustive-release
criteria under ADR-0117/ADR-0105, preserving originals. Finish corrected browser
and isolated review before marking done. Windows stays with the owner.
Counts remain 40 mapped plus 84 legacy = 124 unfinished.
