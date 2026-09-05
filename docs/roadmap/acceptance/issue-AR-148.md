---
title: "AR-148 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, security]
related:
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-148
candidate_commit: pending
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-148 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `Verifier rejects non-string or noncanonical lowercase 64-hex input before HMAC comparison` | 2026-09-05 | `agency_runtime/core/store/schema.py:2740-2805` |
| 1 | test | `Non-ASCII and oversized signatures return zero without raising` | 2026-09-05 | `tests/test_store_schema_coverage_final_remaining.py:441-464` |
| 2 | file | `Well-formed bounded authority computes the original HMAC and compares with hmac.compare_digest` | 2026-09-05 | `agency_runtime/core/store/schema.py:2697-2805` |
| 2 | test | `Valid signed authority is inserted into a real Store, survives reopen, and raw SQLite cannot forge the verifier` | 2026-09-05 | `tests/test_roster_source_credentials.py:1251-1333` |
| 3 | file | `Identity, timestamps, canonical dependency receipt and exact dependency count are checked before comparison` | 2026-09-05 | `agency_runtime/core/store/schema.py:2740-2805` |
| 3 | test | `Malformed identity and incomplete or ambiguous dependency graphs are rejected` | 2026-09-05 | `tests/test_store_schema_coverage_final_remaining.py:240-338` |
| 3 | test | `Receipt canonicalization, schema, closure and empty dependency graphs are rejected` | 2026-09-05 | `tests/test_store_schema_coverage_final_remaining.py:340-377` |
| 3 | test | `Invalid chronology rejects authority after receipt parsing` | 2026-09-05 | `tests/test_store_schema_coverage_final_remaining.py:419-438` |
| 4 | command-output | `All 401 selected schema, Store, credential, native-child ledger and release tests pass warning-strict` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md#current-verification` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
