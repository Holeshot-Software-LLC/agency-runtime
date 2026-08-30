---
title: "AR-171: Redact dashboard lifecycle reasons"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [dashboard, privacy, security, workforce, observability]
related:
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - agency_runtime/core/store/workforce.py
  - agency_runtime/dashboard/dashboard-render.js
  - agency_runtime/server/dashboard.py
  - tests/test_dashboard.py
  - tests/test_workforce_lifecycle.py
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-171
priority: p1
tracker_url: null
depends_on: [AR-153, AR-166]
blocks: []
---

# AR-171: Redact dashboard lifecycle reasons

## Problem

The dashboard requested worker evidence with
`include_history_documents=False`, but the reduced Store projection still
returned the full free-form lifecycle `reason`. A reason can contain an owner
note or other content and was allowed to be much larger than the metadata
needed for the monitoring view. The response therefore contradicted the
document-redaction contract and the dashboard's runtime-metadata disclosure.

## Current state

The reduced worker-history query removes the raw reason and every content-
derived hash from its result. It returns only whether a reason exists, while
the full owner Store API retains the original document for governed history.
The browser renders `Reason recorded` and never receives or interpolates the
free-form reason.

## Approach

Keep full lifecycle documents behind the explicit full-history Store mode.
Project only bounded presence metadata for dashboard worker detail, test the
serialized response for both raw sentinel and derivative-hash absence, and
render inert fixed text. An unsalted reason hash is deliberately excluded
because common operator notes are low-entropy and the hash would expose stable
equality without providing an independently verifiable receipt.

## Dependencies

ADR-0029 requires bounded local observability and truthful privacy disclosure.
AR-153 owns complete but bounded worker-detail delivery; AR-166 owns the
dashboard's visible metadata-versus-governed-definition distinction.

Tracker creation remains pending explicit outward-write authorization.

## Acceptance

- [x] Reduced worker-history responses contain no raw lifecycle reason or
  evidence document.
- [x] No content-derived reason hash permits offline confirmation or cross-
  event equality; only a bounded presence flag reaches the dashboard.
- [x] Presence metadata is bounded and cannot be interpreted as raw HTML.
- [x] Full Store history preserves the original governed lifecycle document.
- [x] Store, dashboard HTTP, and browser regressions prove sentinel content is
  absent from the reduced serialized response and rendered text.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

Focused workforce, dashboard, and browser tests cover raw/full versus redacted
projections, fixed receipt rendering, and sentinel absence. Final aggregate
counts are added after the final integrated gate.
