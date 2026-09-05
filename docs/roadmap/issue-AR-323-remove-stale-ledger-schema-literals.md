---
title: "AR-323: Remove stale native-child ledger schema literals"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-09-05
tags: [bug, testing, store, schema, native-child]
related:
  - docs/roadmap/acceptance/issue-AR-323.md
  - docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
  - docs/roadmap/pre-tracker-history.txt
  - tests/test_schema_v36_invariants.py
  - tests/test_roster_source_credentials.py
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

The defect remains relevant but is stale test coupling, not a broken migration.
At source e4255836 the same three native-child cases fail against schema 49;
seven additional migration/credential-redaction cases have the identical stale
46 assertion. AR-148's malformed-signature repair itself is already present.
Remove the copied current-version literals across these three test files while
preserving explicit legacy input versions and every behavioral assertion.
The seven-file storage/ledger/release package now passes all 401 tests. Production
schema and migration code are unchanged. Isolated acceptance is pending.

AR-347 already placed AR-323 in the guarded pre-tracker history list. The old
active-task prohibition and future tracker-creation prerequisite are historical;
the current task follows that existing exemption rather than creating a
redundant tracker during backlog cleanup.

## Historical state at filing

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
- [ ] Existing pre-tracker exemption and canonical tracker mapping agree with AR-347.

## Historical tracker condition

The original fourth criterion was: "A same-repository tracker issue is created
and linked after explicit authorization." AR-347 subsequently established the
guarded exemption that already contains AR-323. Reconcile that administrative
condition with accepted tracker history; the three product/test criteria remain
unchanged. No exemption list or validator is modified.
