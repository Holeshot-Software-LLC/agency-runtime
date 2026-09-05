---
title: "AR-148: Fail malformed remediation signatures closed"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-09-05
tags: [security, sqlite, remediation, hmac, availability]
related:
  - docs/roadmap/acceptance/issue-AR-148.md
  - docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - agency_runtime/core/store/schema.py
  - tests/test_store_schema_coverage_final_remaining.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-148
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-148: Fail malformed remediation signatures closed

## Problem

The SQLite remediation-authority verifier passed any 64-character string to
`hmac.compare_digest`. A non-ASCII string of that length raises
`TypeError` instead of returning an invalid-authority result, turning
malformed durable input into an availability failure.

## Current state

Canonical signatures are lowercase SHA-256 hex. The verifier now validates that
exact lexical domain before constant-time comparison and returns zero for
non-ASCII, non-hex, wrong-case, short, or oversized values. The repair in
093241033300da2347baa898728ef89f6f5df92f remains present; no production change
is needed. Fresh validation found unrelated stale schema-46 assertions in
AR-323, not a signature defect. After that test-only repair, all 401 selected
schema, Store, credential, ledger and release-contract tests pass. The original
four acceptance criteria are exposed as checkboxes; isolated verification is
pending. Legacy tracker exemption applies; no external issue is claimed.

## Approach

Keep the existing length-framed authority receipt and HMAC construction
unchanged. Add one bounded exact-lowercase-hex guard at the verification
boundary, then retain `compare_digest` for every well-formed candidate.

## Dependencies

AR-95 defines complete durable remediation authority. ADR-0012 makes SQLite the
canonical evidence store and requires malformed durable state to fail closed.

## Acceptance

- [ ] Malformed, non-ASCII, non-hex, wrong-length, or wrong-case signatures return invalid authority without raising.
- [ ] Canonical valid signatures continue through constant-time comparison.
- [ ] Dependency closure, identity, chronology, and receipt checks remain intact.
- [ ] Integrated schema and release suites pass.

## Implementation evidence

Focused schema/HMAC verification passes 58 tests. The broader Store, schema,
roster, and workforce package passes 434 tests with 2 skips. Full integrated
release evidence and authorized tracker creation remain pending.
