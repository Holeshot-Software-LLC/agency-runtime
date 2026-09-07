---
title: "AR-172 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, roster, dashboard]
related:
  - docs/roadmap/issue-AR-172-make-roster-pages-snapshot-consistent.md
  - docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-172
candidate_commit: dec1bc512462285cf4d43742c3e666e6d776186e
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-172 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | One transaction captures generation, exact total and bounded rows | 2026-09-07 | agency_runtime/core/store/roster.py:1850-1904 |
| 1 | file | Public HTTP uses only the composite snapshot for page and count | 2026-09-07 | agency_runtime/server/http.py:607-634 |
| 1 | test | Deterministic writer interleaves after the read snapshot starts | 2026-09-07 | tests/test_roster_snapshot_generation.py:161-203 |
| 1 | command-output | Full focused Store and HTTP run | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#store-and-http-transcript |
| 2 | file | SQL uses single JSON disabled parameter and bound cursor/limit; protects coordinators | 2026-09-07 | agency_runtime/core/store/roster.py:1850-1904 |
| 2 | file | Typed activation caps disabled lists and slugs and rejects protected coordinators | 2026-09-07 | agency_runtime/core/agent_activation.py:9-41 |
| 2 | test | Executed SQL uses json_each and limit plus one | 2026-09-07 | tests/test_roster_snapshot_generation.py:115-159 |
| 2 | test | Oversized disabled lists and protected coordinator disable requests fail | 2026-09-07 | tests/test_agent_activation.py:52-73 |
| 2 | command-output | Full focused activation and Store suites pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#store-and-http-transcript |
| 3 | test | Reader retains generation two and two rows while writer reaches generation three | 2026-09-07 | tests/test_roster_snapshot_generation.py:161-203 |
| 3 | file | BEGIN precedes generation/count/page reads on the same connection | 2026-09-07 | agency_runtime/core/store/roster.py:1850-1904 |
| 3 | command-output | Concurrent activation test runs in the complete snapshot suite | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#store-and-http-transcript |
| 4 | file | Control and operational handlers bind configuration and Store generation | 2026-09-07 | agency_runtime/server/dashboard.py:1998-2104 |
| 4 | file | Primary and exact lookup handlers emit both revisions | 2026-09-07 | agency_runtime/server/dashboard.py:2440-2537 |
| 4 | file | Shared Store response identity includes the captured configuration revision | 2026-09-07 | agency_runtime/server/dashboard.py:350-361 |
| 4 | file | Collection checks initial and subsequent revisions; roster wrapper selects both fields | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1402-1490 |
| 4 | file | Operational paging selects both revision fields and expected control configuration | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1699-1712 |
| 4 | file | Current control caller binds primary, exact and operational paths to its configuration | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:1972-2011 |
| 4 | test | Both refresh modes reject all five config drift paths under fixed Store revision | 2026-09-07 | tests/dashboard_ui.test.mjs:6681-6761 |
| 4 | command-output | All ten path regressions pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#config-drift-regression-transcript |
| 5 | test | Baseline state remains unchanged and control is stale on five kinds of drift in both refreshes | 2026-09-07 | tests/dashboard_ui.test.mjs:6681-6761 |
| 5 | file | Full refresh commits only after all collection checks, otherwise marks stale | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2128-2204 |
| 5 | file | Control-only refresh likewise commits only a validated snapshot | 2026-09-07 | agency_runtime/dashboard/dashboard-live.js:2080-2126 |
| 5 | command-output | Ten direct state-preservation cases pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#config-drift-regression-transcript |
| 5 | command-output | Complete UI suite and coverage remain above current floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#full-ui-and-coverage-transcript |
| 6 | file | Generation comparison precedes publication, with bounded failure | 2026-09-07 | agency_runtime/server/dashboard.py:266-287 |
| 6 | file | Original bounded capture limit is three total attempts | 2026-09-07 | agency_runtime/server/dashboard.py:180-185 |
| 6 | test | A single mismatch recovers once; persistent churn raises at the bound | 2026-09-07 | tests/test_dashboard_server_coverage_complete.py:545-578 |
| 6 | command-output | Full dashboard server suite includes both recapture branches | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#store-and-http-transcript |
| 7 | file | Existing policy makes exhaustive integration optional and names bounded delivery | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |
| 7 | command-output | Actual Store/HTTP/activation command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#store-and-http-transcript |
| 7 | command-output | Actual full UI and current-floor coverage command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#full-ui-and-coverage-transcript |
| 7 | command-output | Actual named production spine command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#production-spine-transcript |
| 7 | command-output | Actual metadata/policy/worklog/strict docs/tracker/Ruff/diff outputs | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-172-roster-snapshots-20260907.md#record-checks |

## Verification

Pending isolated checks after the source, test and actual gate transcripts are
committed and this record freezes their immutable candidate.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
