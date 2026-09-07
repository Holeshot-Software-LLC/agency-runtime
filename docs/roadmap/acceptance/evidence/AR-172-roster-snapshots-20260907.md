---
title: "AR-172 current roster snapshot evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, roster, sqlite, dashboard, backlog]
related:
  - docs/roadmap/issue-AR-172-make-roster-pages-snapshot-consistent.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0046-config-backed-agent-activation-policy.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/core/store/roster.py
  - agency_runtime/server/dashboard.py
  - agency_runtime/server/http.py
  - agency_runtime/dashboard/dashboard-live.js
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
---

# AR-172: Roster snapshot consistency

## Scope and source identity

September 7, 2026, Linux / Python 3.12.3 / Node 22.23.2, after clean
8f9d9e4cf4b9720d9e00ff1b109683abb7c61ce3 (PR #720 plus its merge ledger).
Production, scripts and workflows are unchanged. An 81-line table adds ten
DOM regressions against existing refresh behavior; no test fails before any
production repair because no production repair is needed.

SQLite owns roster generation/count/rows in one read transaction. Disabled
slugs use a single JSON SQL parameter, the cursor and limit are bound, and
protected coordinators are subtracted from the disabled set. Typed activation
configuration caps the set at 4096 canonical bounded slugs.

The control handler takes one configuration state for both projections,
compares their Store generations, and publishes only a matched pair. The
three-attempt limit was already present with criterion 6 in original commit
3e14f7404. A single injected mismatch recovers on attempt two; persistent churn
exhausts the unchanged bound and raises. This is not an additional retry or
an acceptance relaxation.

## Store and HTTP transcript

Command (owned-tree PYTHONPATH, temporary isolated profiles):

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_roster_snapshot_generation.py tests/test_senior_audit_hardening.py tests/test_dashboard_server_coverage_complete.py tests/test_dashboard_operational.py tests/test_dashboard.py tests/test_agent_activation.py -q -W error
```

Exact stdout, exit zero:

```text
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 77%]
..............................................................           [100%]
278 passed in 59.46s
```

These full suites include SQL inspection, concurrent activation interleaving,
public HTTP envelope/bounds, control recapture, dashboard primary/operational
paging and protected activation policy. Real loopback HTTP uses temporary
profiles, not the owner service. No native-host activation is claimed.

## Config drift regression transcript

```bash
node --test --test-name-pattern='config drift in' tests/dashboard_ui.test.mjs
```

Exact stdout, exit zero:

```text
TAP version 13
# Subtest: refreshAll retains last-good control state on config drift in initial
ok 1 - refreshAll retains last-good control state on config drift in initial
  ---
  duration_ms: 11.611209
  type: 'test'
  ...
# Subtest: refreshAll retains last-good control state on config drift in primary-page
ok 2 - refreshAll retains last-good control state on config drift in primary-page
  ---
  duration_ms: 0.905691
  type: 'test'
  ...
# Subtest: refreshAll retains last-good control state on config drift in exact
ok 3 - refreshAll retains last-good control state on config drift in exact
  ---
  duration_ms: 0.813763
  type: 'test'
  ...
# Subtest: refreshAll retains last-good control state on config drift in operational-initial
ok 4 - refreshAll retains last-good control state on config drift in operational-initial
  ---
  duration_ms: 0.700477
  type: 'test'
  ...
# Subtest: refreshAll retains last-good control state on config drift in operational-page
ok 5 - refreshAll retains last-good control state on config drift in operational-page
  ---
  duration_ms: 0.762265
  type: 'test'
  ...
# Subtest: refreshControlPlane retains last-good control state on config drift in initial
ok 6 - refreshControlPlane retains last-good control state on config drift in initial
  ---
  duration_ms: 0.542582
  type: 'test'
  ...
# Subtest: refreshControlPlane retains last-good control state on config drift in primary-page
ok 7 - refreshControlPlane retains last-good control state on config drift in primary-page
  ---
  duration_ms: 0.402687
  type: 'test'
  ...
# Subtest: refreshControlPlane retains last-good control state on config drift in exact
ok 8 - refreshControlPlane retains last-good control state on config drift in exact
  ---
  duration_ms: 0.484314
  type: 'test'
  ...
# Subtest: refreshControlPlane retains last-good control state on config drift in operational-initial
ok 9 - refreshControlPlane retains last-good control state on config drift in operational-initial
  ---
  duration_ms: 0.697937
  type: 'test'
  ...
# Subtest: refreshControlPlane retains last-good control state on config drift in operational-page
ok 10 - refreshControlPlane retains last-good control state on config drift in operational-page
  ---
  duration_ms: 0.639649
  type: 'test'
  ...
1..10
# tests 10
# suites 0
# pass 10
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 78.778055
```

Both refreshAll and refreshControlPlane first commit a valid baseline. With
Store revision held fixed, each then receives changed configuration on its
initial roster, next primary page, exact lookup, initial operational page or
next operational page. Config/hosts/roster/counts/snapshots/reviews/operations
and live revision remain the prior values; control becomes stale and shows the
retained-state notice. Request counts prove processing stops at the mismatch.

## Full UI and coverage transcript

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Exact final stdout excerpt, exit zero; floors unchanged:

```text
type: 'test'
  ...
1..200
# tests 204
# suites 0
# pass 204
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 249.990624
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
#   dashboard-live.js    |  95.34 |    87.39 |   98.77 | 63-64 242-244 276-277 360-363 372-373 676 750-751 798-831 852-854 863 875 903-904 938 1229-1230 1237-1238 1354-1355 1362 1441-1442 1627-1628 1767-1769 1784-1787 1796-1799 1893 1924-1925 1938-1940 1964-1966 1969-1970 2045-2046 2048-2049 2060-2061 2215 2248 2356-2364 2378-2382 2390-2391 2400-2401 2431-2432
#   dashboard-render.js  |  97.96 |    86.25 |   97.01 | 120-128 777-782 896-897 933-935 1458 1461-1462 1494-1495 1654-1655 1923-1928 2323-2340
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# all files              |  96.93 |    86.78 |   95.73 | 
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# end of coverage report
```

## Production spine transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_storage_file_trust.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_upstream_selection_eval.py tests/test_decision_conformance.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_owner_authority.py tests/test_security_turn_boundaries.py tests/test_canary_coverage_complete.py tests/test_complexity_refactors.py tests/test_coverage_final_host_cli.py tests/test_resident_manager_lifecycle.py -q -W error
```

Exact stdout, exit zero:

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
1085 passed, 3 skipped in 69.71s (0:01:09)
```

No skips added. The three existing skips are retained unchanged. This is the
named fast spine, not the exhaustive corpus, coverage shards or matrix.

## Record checks

Commands (set -e; PYTHONPATH=.):

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/docs_metadata.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_policy_availability.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_worklog.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_docs.py --require-tracker
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_tracker.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime tests scripts
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format --check agency_runtime tests scripts
git diff --check
```

Exact stdout, exit zero; silent commands also returned zero:

```text
checked 1201 Markdown documents
worklog index is current (2009 commits)
documentation validation passed for 1201 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```

The snapshot has 1201 maintained Markdown documents before its worklog detail.
The receipt records real output observed before candidate freeze, not a future
CI result. No hosted green is inferred.

Unchanged Python source/scripts comparison (exit zero, empty stdout):

```bash
git diff --exit-code 9effff3f6c4f4fbe59de8793df074a041e64dab9 HEAD -- 'agency_runtime/**/*.py' 'scripts/*.py'
```

This supports reuse of the earlier
[AR-165 curated conformance receipt](AR-165-dependency-capability-20260907.md),
not a new run or a JavaScript mutation-coverage claim.

## Limits

This package verifies existing Store/HTTP/production-DOM behavior. It does not
claim a newly installed wheel, full-browser accessibility, native harness
activation, hosted CI, Windows or a complete release. The fresh deterministic
routing evaluation passes all 39 gates; its candidate-recall-only/synthetic
contract is not a staffing latency or hiring-quality measurement. AR-165's
184/184 curated Python conformance receipt is earlier evidence, not a new run.
Only criterion 7 is reconciled under existing ADR-0105; original text remains.
