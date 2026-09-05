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
candidate_commit: 11371cb6a14d91ebe998ea249f8c5545f49e5705
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
| 1 | satisfied | `AR-148.1-20260905-810e19b1` | `252ec8901c3ed9a8002eebfb9b4f56b0212c7eabc858445ea8d3ca5374f6f024` | 2026-09-05 | schema.py:2740-2805 returns 0 for non-string signatures or strings outside lowercase 64-hex before HMAC comparison; tests at lines 441-464 assert rejection of non-ASCII and oversized signatures. |
| 2 | satisfied | `AR-148.2-20260905-5c903860` | `3d2f29c6e506bf51f47b0b70572e52d03ee6c61afd4aa8d5ad63b16735aa8151` | 2026-09-05 | schema.py:2697-2805 computes the expected SHA-256 HMAC for valid bounded inputs and compares canonical 64-character lowercase hexadecimal signatures using hmac.compare_digest. |
| 3 | satisfied | `AR-148.3-20260905-c007da4a` | `b49c93213f6335380f4016ea77075beb50d4ee31f8b3ad4861aac1bb1fe15a6d` | 2026-09-05 | schema.py:2740-2805 enforces identity, chronology, receipt parsing and dependency counts; tests at lines 240-377 cover rejection of incomplete dependency closure and malformed receipts. |
| 4 | satisfied | `AR-148.4-20260905-a9b9b7ac` | `72b9855012840e9d59702d0d3811cb55641653b5284ac4130eb4d823a8fff62e` | 2026-09-05 | The Current verification excerpt in AR-323-current-schema-verification-20260905.md records 401 passing warning-strict tests across seven files, including schema, Store, release packaging, and release contract suites. |
