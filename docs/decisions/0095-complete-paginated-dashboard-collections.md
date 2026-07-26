---
title: "Dashboard collection views expose complete paginated truth"
status: accepted
category: decisions
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, pagination, ui, truth, operations]
related:
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
supersedes: []
superseded_by: null
id: ADR-0095
type: decision
deciders: [maintainers]
---

# ADR-0095: Dashboard collection views expose complete paginated truth

## Context

The dashboard's safety caps are necessary, but a capped page is not the full
workforce. When an API silently reduces the requested limit and the UI derives
totals from that page, a safe transport limit becomes a false product claim.
The bundled workforce already exceeds the generic page cap.

## Decision

Every dashboard collection response declares its stable cursor, page size,
`next_cursor`, `truncated` state, filtered total, and global total where
applicable. Totals are computed independently of the page. The UI labels page
and population counts separately and either follows all pages or deliberately
virtualizes them.

Cursors bind the collection's stable ordering and documented snapshot/revision
semantics. A caller cannot infer completeness merely because fewer than its
requested limit were returned.

## Consequences

- Safety bounds remain while the UI stops hiding workers and cases.
- Large collections require multiple bounded requests.
- Concurrent insertion behavior must be defined and tested per collection.
- Collection response schemas become versioned contracts.

## Alternatives

- **Raise every cap above the current roster size.** Rejected because the defect
  recurs at the next size and weakens resource bounds.
- **Display only the first page without totals.** Rejected for operational views
  that claim workforce and case completeness.
- **Return the entire collection.** Rejected because bounded responses are a
  security and performance requirement.
