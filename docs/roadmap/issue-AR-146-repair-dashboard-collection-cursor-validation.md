---
title: "AR-146: Repair dashboard collection cursor validation"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-08-12
tags: [dashboard, pagination, traceability, correctness]
related:
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - agency_runtime/server/dashboard.py
  - tests/test_dashboard_server_coverage_complete.py
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-146
priority: p0
tracker_url: null
depends_on:
  - AR-137
blocks: [AR-172]
---

# AR-146: Repair dashboard collection cursor validation

## Problem

The dashboard generated URL-safe opaque collection cursors that its own
validator rejected. Every activity request carrying a generated `after` cursor
therefore failed before reaching Store keyset pagination.

## Current state

The validator regex used a raw-string literal `\\Z`, matching a backslash and
the letter Z instead of the end-of-string anchor `\Z`. Focused round-trip and
HTTP activity tests reproduced the failure for a cursor emitted by
`_encode_collection_cursor`.

## Approach

Correct the regex anchor and lock the complete browser-to-handler-to-Store
contract with canonical round-trip, malformed encoding, wrong-kind,
wrong-arity, empty-field, pagination, redaction, and cursor-projection tests.

## Dependencies

AR-137 defines complete dashboard collection and keyset semantics.

## Acceptance

- [x] Every generated cursor decodes with its exact collection kind and arity.
- [x] Malformed, wrong-kind, wrong-arity, empty, and non-string cursor values fail
  closed.
- [x] `/api/activity` passes decoded keyset fields to the Store and returns a
  decodable next cursor.
- [x] Cursor payloads remain bounded, opaque, and free of sensitive content.

## Implementation evidence

The regex now uses the correct end anchor. The focused dashboard server suite
passes 29 tests, existing cursor/activity/observation regressions pass 12 tests,
and new behavioral coverage exercises canonical and hostile cursor paths.
Tracker creation remains pending explicit outward-action authorization.
