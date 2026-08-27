---
title: "AR-323: Remove stale native-child ledger schema literals"
status: open
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, testing, store, schema, native-child]
related:
  - docs/roadmap/AR-119-vision-loop-status.md
  - agency_runtime/core/store/schema.py
  - tests/test_native_child_delivery_verification_ledger.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-323
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-323: Remove stale native-child ledger schema literals

## Problem

Three optional native-child delivery-ledger tests hard-code Store schema 46.
The current repository and origin/main both define and materialize schema 48,
so those assertions fail before exercising the ledger invariants they own.

## Current state

- The wider AR-322 hook regression command passes 266 tests and fails these
  three assertions only; the failures expect 46 and observe 48.
- `SCHEMA_VERSION` is already imported by the affected test module and equals
  48. The delivery-verification schema checks following the stale literals are
  not implicated.
- Historical AR-119 status already noted the same drift at schema 47, so this
  predates AR-322 and is not caused by its request-digest binding.
- This file is not part of the named fast Python production spine. The finding
  does not expand AR-322 or independently force AR-297 to NO-GO.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Replace fixed current-version assertions with the canonical `SCHEMA_VERSION`
constant while retaining explicit prior-version migration fixtures. Run the
focused ledger suite and storage/security consumers, then record exact evidence
without changing the production schema or migration contract.

## Dependencies

None. Coordinate with any future schema increment so the tests continue to
assert the canonical current version rather than another copied literal.

## Acceptance

- [ ] Current-schema assertions derive from `SCHEMA_VERSION`.
- [ ] Prior schema fixtures still prove repair of the delivery ledger.
- [ ] Focused storage and native-child ledger tests pass warning-strict.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
