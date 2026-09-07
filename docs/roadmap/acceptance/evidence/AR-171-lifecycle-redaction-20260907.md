---
title: "AR-171 current lifecycle redaction evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, privacy, dashboard, workforce, backlog]
related:
  - docs/roadmap/issue-AR-171-redact-dashboard-lifecycle-reasons.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/core/store/workforce.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-render.js
  - tests/test_workforce_lifecycle.py
  - tests/test_dashboard.py
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
---

# AR-171: Lifecycle reason redaction evidence

## Scope and implementation

September 7, 2026, Linux / Python 3.12.3 / Node 22.23.2, after clean
05d7696a55922387c32aa7bda31a75bc58370cfb (PR #719 plus its merge ledger).
No production/script/workflow change; only one 29-line DOM regression is added.
This verifies the existing privacy implementation, not a new redaction algorithm.

Reduced Store history explicitly selects event metadata, removes reason and
emits bool(reason). Evidence documents and content-derived reason hashes are
not selected. Full-history mode returns the exact reason and decoded original
evidence. Dashboard worker detail explicitly requests reduced history.
The renderer tests reason_present === true and emits only fixed Reason recorded
text; it never reads reason, reason_hash or evidence. Invalid flag types do
not become content or HTML. Governed prompt definitions and accepted outcome
manifests have separate authorities; this record does not remove them.

## Store and HTTP transcript

Command, executed with PYTHONPATH=. pointing to the owned worktree:

```bash
python -m pytest tests/test_workforce_lifecycle.py tests/test_dashboard.py -q -W error
```

Exact stdout (exit zero):

```text
........................................................................ [ 36%]
........................................................................ [ 72%]
.......................................................                  [100%]
199 passed in 48.66s
```

The Store regression inserts a private reason and large event/outcome documents,
then compares full and reduced projections and serialized bytes. It explicitly
checks absence of the raw reason, its SHA-256, event evidence and outcome content.
The real authenticated loopback HTTP test disables a contractor with an owner
note and checks the returned worker-history JSON has only its presence flag,
not reason, hash or the note's sentinel. These are isolated temporary profiles;
no owner service or native host is mutated.

## Renderer regression transcript

Command:

```bash
node --test --test-name-pattern='lifecycle reason presence' tests/dashboard_ui.test.mjs
```

Exact stdout (exit zero):

```text
TAP version 13
# Subtest: lifecycle reason presence renders fixed text and never raw content or hashes
ok 1 - lifecycle reason presence renders fixed text and never raw content or hashes
  ---
  duration_ms: 2.990219
  type: 'test'
  ...
1..1
# tests 1
# suites 0
# pass 1
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 60.397286
```

The production renderer receives eight presence values, with deliberately
injected raw HTML/note, reason hash and evidence fields. Only primitive true
displays Reason recorded; no sentinel/hash text or IMG node is created.
This is DOM regression evidence, not a native-host or full accessibility claim.

## Full UI and coverage transcript

Command:

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Exact final stdout excerpt (exit zero; limits unchanged):

```text
  type: 'test'
  ...
1..190
# tests 194
# suites 0
# pass 194
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 234.114242
# start of coverage report
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# file                   | line % | branch % | funcs % | uncovered lines
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# agency_runtime         |        |          |         | 
#  dashboard             |        |          |         | 
#   app.js               |  95.45 |    87.96 |   71.70 | 431 467-469 483-490 515-520 524-525 530-536
#   charts.js            | 100.00 |   100.00 |  100.00 | 
#   dashboard-actions.js |  94.53 |    47.10 |  100.00 | 128-129 132-133 149 159-160 176-177 211-214 243 252-253 276 311 319-320 348 389-390 393-394 429 473
#   dashboard-config.js  |  99.28 |    96.69 |  100.00 | 230-231 291-292
#   dashboard-core.js    |  99.05 |    92.98 |  100.00 | 345-346 449 482-483
#   dashboard-live.js    |  95.34 |    87.35 |   98.77 | 63-64 242-244 276-277 360-363 372-373 676 750-751 798-831 852-854 863 875 903-904 938 1229-1230 1237-1238 1354-1355 1362 1441-1442 1627-1628 1767-1769 1784-1787 1796-1799 1893 1924-1925 1938-1940 1964-1966 1969-1970 2045-2046 2048-2049 2060-2061 2215 2248 2356-2364 2378-2382 2390-2391 2400-2401 2431-2432
#   dashboard-render.js  |  97.96 |    86.24 |   97.01 | 120-128 777-782 896-897 933-935 1458 1461-1462 1494-1495 1654-1655 1923-1928 2323-2340
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# all files              |  96.93 |    86.77 |   95.73 | 
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# end of coverage report
```

## Production spine transcript

Fresh named spine, PYTHONPATH=. and umask 077:

```bash
python -m pytest \
  tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py \
  tests/test_executable_namespace_security.py tests/test_storage_file_trust.py \
  tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py \
  tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py \
  tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py \
  tests/test_upstream_selection_eval.py tests/test_decision_conformance.py \
  tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py \
  tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py \
  tests/test_cli_parser_contract.py tests/test_cli_upgrade.py \
  tests/test_update_service.py tests/test_native_installer.py \
  tests/test_host_uninstall.py tests/test_cli_uninstall.py \
  tests/test_host_boundary_hardening.py tests/test_cli_owner_authority.py \
  tests/test_security_turn_boundaries.py tests/test_canary_coverage_complete.py \
  tests/test_complexity_refactors.py tests/test_coverage_final_host_cli.py \
  tests/test_resident_manager_lifecycle.py -q -W error
```

Exact stdout (exit zero):

```text
........................................................................ [  6%]
........................................................................ [ 13%]
........................................................................ [ 19%]
..................................s..................................... [ 26%]
........................................................................ [ 33%]
........................................................................ [ 39%]
........................................................................ [ 46%]
........................................................................ [ 52%]
........................................................................ [ 59%]
....................................................................ss.. [ 66%]
........................................................................ [ 72%]
........................................................................ [ 79%]
........................................................................ [ 86%]
........................................................................ [ 92%]
........................................................................ [ 99%]
........                                                                 [100%]
1085 passed, 3 skipped in 67.57s (0:01:07)
```

Three skips are pre-existing; no new skip, xfail or relaxed threshold.

## Record checks

Commands run sequentially with stop-on-first-error, all exit zero:

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py --require-tracker
python scripts/verify_tracker.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
```

Exact combined stdout (policy/diff checks are silent on success):

```text
checked 1198 Markdown documents
worklog index is current (2005 commits)
documentation validation passed for 1198 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```

This validates the implementation/evidence working tree before its substantive
commit and immediate worklog ledger. Candidate freeze changes only the record's
commit reference; no production/script/workflow bytes change.

## Scope of acceptance

Only criterion 6 changes under existing ADR-0105; its original wording and
criteria 1–5 are preserved. No exhaustive corpus/matrix, workflow dispatch,
native Windows or new installed-host canary is claimed. The live component
of this bounded package is the real authenticated loopback HTTP interaction;
rendering uses the production DOM module, not a full native-host activation.

## Completion

All six criteria satisfy in the first isolated review at
8a8db2aeeae788829ae7dfc641142d7c04376e6e, without retry. AR-171 is done; runtime
source remains unchanged. The existing legacy exemption applies, so no duplicate
tracker is created. Queue becomes 40 mapped plus 83 legacy = 123 unfinished.
