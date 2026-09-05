---
title: "AR-323 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, schema]
related:
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-323
candidate_commit: 11371cb6a14d91ebe998ea249f8c5545f49e5705
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-323 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Current ledger schema and migration output both equal the imported canonical SCHEMA_VERSION` | 2026-09-05 | `tests/test_native_child_delivery_verification_ledger.py:200-285` |
| 1 | test | `Current consumption schema retains behavioral assertions and compares with the canonical version` | 2026-09-05 | `tests/test_schema_v36_invariants.py:59-88` |
| 1 | test | `Legacy credential migration still asserts current schema and redaction behavior` | 2026-09-05 | `tests/test_roster_source_credentials.py:1747-1785` |
| 2 | test | `Explicit legacy 44/45 stores with a dropped ledger migrate and restore the required ledger schema` | 2026-09-05 | `tests/test_native_child_delivery_verification_ledger.py:261-285` |
| 2 | test | `Exact column, uniqueness, one-use trigger and cascade constraints remain asserted` | 2026-09-05 | `tests/test_native_child_delivery_verification_ledger.py:200-258` |
| 3 | command-output | `401 complete selected storage, migration, credentials, ledger and release tests pass warning-strict` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md#current-verification` |
| 4 | file | `The accepted tracker reconciliation established a guarded pre-tracker list` | 2026-09-05 | `docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:113-121` |
| 4 | file | `AR-323 is already in that canonical exemption list` | 2026-09-05 | `docs/roadmap/pre-tracker-history.txt:124-134` |
| 4 | file | `Canonical issue retains null tracker URL and documents the administrative reconciliation` | 2026-09-05 | `docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md:1-62` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-323.1-20260905-b8d063e5` | `d41ca30323b011c3f11fc09a8b182ba83b13b749c3d8b62f2c77f44fb68d7899` | 2026-09-05 | The excerpts from test_native_child_delivery_verification_ledger.py, test_schema_v36_invariants.py, and test_roster_source_credentials.py all compare current schema versions directly with SCHEMA_VERSION. |
| 2 | satisfied | `AR-323.2-20260905-604ba534` | `b2eb34bf25f637b901647b6a53320d5101170c3b6a16735e9267c76ec69d2daf` | 2026-09-05 | tests/test_native_child_delivery_verification_ledger.py:261-285 covers prior versions 44 and 45, drops the ledger, reopens Store, and asserts restoration of the current ledger schema and schema version. |
| 3 | satisfied | `AR-323.3-20260905-feb2822d` | `90049f4513e0dedcdda5c5e981077ff59edacf0449ed21c69c647b330fae0069` | 2026-09-05 | The Current verification excerpt in AR-323-current-schema-verification-20260905.md records focused storage and native-child delivery-ledger tests run with -W error, with all 401 tests passing. |
| 4 | satisfied | `AR-323.4-20260905-492f66db` | `a49aec4a384bd85f92074e38df6a0ebcae931c55aaa2224747502d857c5f4d8b` | 2026-09-05 | AR-347 documents the guarded pre-tracker exemption, pre-tracker-history.txt includes AR-323, and AR-323's canonical issue retains tracker_url: null and explicitly records agreement with AR-347. |
