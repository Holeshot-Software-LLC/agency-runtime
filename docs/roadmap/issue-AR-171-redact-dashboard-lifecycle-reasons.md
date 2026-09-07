---
title: "AR-171: Redact dashboard lifecycle reasons"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [dashboard, privacy, security, workforce, observability]
related:
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-171-lifecycle-redaction-20260907.md
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

September 7 inspection confirms this privacy boundary already exists; no runtime
repair is needed. Full Store/workforce and dashboard HTTP suites pass 199 tests.
The production renderer passes a new eight-value presence-flag/sentinel
regression and all 194 UI tests with unchanged coverage floors. The new test
deliberately supplies unexpected private fields to prove inert rendering; real
HTTP tests separately prove those fields never leave the reduced Store response.
Exact commands and raw results are in the
[receipt](acceptance/evidence/AR-171-lifecycle-redaction-20260907.md).

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

The existing pre-tracker exemption applies; no duplicate tracker is created.
ADR-0105 replaces only the obsolete final exhaustive-release criterion with
bounded Store/HTTP/UI and named-spine verification; original wording remains.

## Acceptance

- [x] Reduced worker-history responses contain no raw lifecycle reason or
  evidence document.
- [x] No content-derived reason hash permits offline confirmation or cross-
  event equality; only a bounded presence flag reaches the dashboard.
- [x] Presence metadata is bounded and cannot be interpreted as raw HTML.
- [x] Full Store history preserves the original governed lifecycle document.
- [x] Store, dashboard HTTP, and browser regressions prove sentinel content is
  absent from the reduced serialized response and rendered text.
- [ ] Focused Store, dashboard HTTP and UI regressions/current coverage floors,
  the named production spine, metadata, policy, worklog, strict docs/tracker,
  Ruff and diff checks pass; exhaustive integration remains optional.

## Preserved original verification criterion

Original criterion 6: The final repository release gate passes at the
implementation commit. ADR-0105 governs the explicit bounded replacement;
criteria 1–5 remain unchanged.

## Implementation evidence

Current workforce, real loopback HTTP and production-renderer DOM tests cover
raw/full versus reduced projections, fixed text and raw/hash sentinel absence.
The runtime source is unchanged. Isolated acceptance is required before the
done flip; no old checkbox is treated as current-candidate proof.
