---
title: "AR-323 and AR-148 current Store verification"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, store, schema, backlog]
related:
  - docs/roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md
  - docs/roadmap/issue-AR-148-fail-malformed-remediation-signatures-closed.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
supersedes: []
superseded_by: null
---

# AR-323 and AR-148 current Store verification

## Present relevance

AR-148's signature guard remains relevant security behavior and was already
implemented in 0932410. It accepts only 64 lowercase hex characters before
constant-time comparison, while preserving identity, chronology, dependency
closure and canonical receipt validation. The existing regression rejects
non-ASCII and oversized signatures; the source guard covers the full malformed
domain. A real Store authority survives reopen and cannot be forged by raw
SQLite without the verifier.

AR-323 is a genuine test-maintenance gap, not evidence that current schema 49
should be rolled back to 46. The old native-child failures share their cause
with seven migration/credential-redaction tests found while verifying AR-148.
The correction references the imported canonical current version, keeping every
explicit historical migration input, column/index/trigger assertion, row and
credential preservation check, and one-use ledger constraint. No product source,
schema version, security policy, skip or coverage floor is changed.

## Red evidence

Linux/Python 3.12 at source e4255836:

- Initial schema/HMAC plus release-packaging files: 157 passed in 4.61s.
- Six-file schema/credential/release expansion: 7 failed, 364 passed in 21.03s.
  Every failure was the copied `version == SCHEMA_VERSION == 46` assertion;
  the materialized and imported current schema were both 49.
- Native-child ledger file: 3 failed, 27 passed in 2.90s. Its current-schema
  test and legacy 44/45 repair cases likewise compared current output with 46.

## Current verification

After the bounded assertion-only repair, using owner-private test process state:

```text
umask 077
python -m pytest \
  tests/test_store_schema_coverage_final_remaining.py \
  tests/test_schema_v17_upgrade.py \
  tests/test_schema_v36_invariants.py \
  tests/test_roster_source_credentials.py \
  tests/test_release_packaging.py \
  tests/test_release_contract.py \
  tests/test_native_child_delivery_verification_ledger.py -q -W error --tb=short
401 passed in 24.47s
```

This is the complete named seven-file package, including real disposable Store
migration/reopen, malformed authority, credential redaction and delivery-ledger
tests, not a mocked schema increment. Ruff passes and all 764 Python files are
already formatted. The current product source is identical to the accepted
installed 5434836e runtime. No exhaustive corpus, coverage matrix, new release
artifact, Windows result or native host activation is inferred from these tests.

A fresh named production-spine run also passes: 1,030 passed, three existing
skips in 63.73s with warnings strict. It uses the exact 29 files named in
AGENTS.md; the focused schema/ledger files above are additional verification.

## Tracker reconciliation

AR-347 established the closed pre-tracker list already containing AR-323.
The canonical issue and registry retain a null external URL and identify that
exemption, instead of claiming an issue exists or creating unnecessary work.
The original future-tracker condition is preserved in the canonical issue's
historical section. Neither the allow-list nor its strict validator is edited.
