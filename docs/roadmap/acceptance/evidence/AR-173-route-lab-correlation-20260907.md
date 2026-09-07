---
title: "AR-173 current Route Lab correlation evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, dashboard, diagnostics, correlation, backlog]
related:
  - docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/core/observability.py
  - agency_runtime/core/selector/explain.py
  - tests/test_dashboard.py
supersedes: []
superseded_by: null
---

# AR-173: Diagnostic Route Lab correlation

## Scope and first checkpoint

Linux / Python 3.12.3 / Node 22.23.2, September 7, 2026, after clean
6afcbcb523d55f4beb2339f2fa5b06c9ecae8a01 (PR #721 plus merge ledger).
No production change. New authenticated HTTP regression uses two actual social
explanations, with a guard that fails if inference is called. A wrapper observes
the real explain_route entry and then calls its unmodified implementation.

Every enabled request's trace is canonical UUIDv4 and already attached to the
active request observation before explanation. Responses preserve exactly
that trace. Each request has a separate client request UUID; its final dashboard
observation joins to the trace's domain-separated digest. The test restricts the
observation to allowed metadata, under 512 UTF-8 bytes, and rejects task, session,
bearer and prompt values. It verifies distinct traces, no run rows, no decision
IDs, zero routing-decision rows and no open session trace.

Additional guards reject trace allocation for invalid task input and master-
disabled requests. The existing bypass test still denies host/catalog access
and now also requires an empty routing trace. All profiles are temporary;
the owner's service, switch, roster and native hosts are untouched.

## Focused HTTP transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_dashboard.py -k 'route_lab_correlates_fresh or route_lab_master_disabled' -q -W error
```

Exact stdout, exit zero:

```text
..                                                                       [100%]
2 passed, 173 deselected in 2.33s
```

Ruff check passes and Ruff format reports the file unchanged after its initial
format. No failing product test was reproduced; the missing regression and
inaccurate record were the findings.

## Reconciliation

The existing explain_route docstring at lines 241–243 dates to e5f4a8c2
(July 18), before AR-173 (July 27). It explicitly retains diagnostic response
identity without durable turn evidence. The old issue narrative's persistence
claim was therefore not a missing implementation obligation.

ADR-0231 explicitly reconciles criteria 1/4/5 before first review. Original wording
is preserved. Disabled/invalid calls do not fabricate traces; request observations
are emitted as log envelopes, not promised disk-retained or SQLite-persisted
turn records. The authenticated diagnostic response can include the task; the
content-free guarantee applies to correlation observations, not that response.

First isolated review at f4f5124e satisfies 1/3/4/5 but contradicts criterion 2:
the response's raw trace and the observation's digest are not equal strings.
All first verdicts are preserved at 941b9025. ADR-0232 explicitly supersedes
ADR-0231 and defines exact equality between the observation digest and the
domain-separated digest of the response trace. Original criterion 2 remains
in the issue. No production/log-field/test change is made; the same actual
HTTP regression already proves this relationship. All five criteria are judged
again at the final candidate, without copying earlier satisfied verdicts.

## Full focused transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_dashboard.py tests/test_explain.py tests/test_runtime_observability.py tests/test_store_observability.py -q -W error
```

Exact stdout, exit zero:

```text
........................................................................ [ 36%]
........................................................................ [ 73%]
...................................................                      [100%]
195 passed in 52.75s
```

This includes the complete dashboard HTTP suite, diagnostic explanation tests
and strict runtime/Store observation contracts. No skips or inference spending
are added by the new regression.

## Full UI and coverage transcript

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Exact final stdout excerpt, exit zero; trailing display padding removed and
coverage floors unchanged:

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
# duration_ms 257.107362
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
1085 passed, 3 skipped in 69.18s (0:01:09)
```

The three existing skips are unchanged; no new skip or xfail.

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

Exact final stdout, exit zero; silent checks also returned zero:

```text
checked 1207 Markdown documents
worklog index is current (2018 commits)
documentation validation passed for 1207 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```

All final-contract record checks pass for 1207 Markdown documents and 397 mapped
trackers, with two historical PR exceptions. This is the fresh rerun after
ADR-0232; the earlier 1206-file result remains at f4f5124e. No hosted CI success
is implied.

## Draft packet check

The first draft check ran after adding builder rows but before appending their
referenced transcript sections. It correctly rejected five missing headings;
set -e stopped the command group before tracker/lint checks. No commit or
acceptance invocation claimed that draft was valid. Exact output, exit one:

```text
checked 1206 Markdown documents
worklog index is current (2015 commits)
ERROR: docs/roadmap/acceptance/issue-AR-173.md: criterion 3 builder Source heading is absent
ERROR: docs/roadmap/acceptance/issue-AR-173.md: criterion 5 builder Source heading is absent
ERROR: docs/roadmap/acceptance/issue-AR-173.md: criterion 5 builder Source heading is absent
ERROR: docs/roadmap/acceptance/issue-AR-173.md: criterion 5 builder Source heading is absent
ERROR: docs/roadmap/acceptance/issue-AR-173.md: criterion 5 builder Source heading is absent
documentation validation failed with 5 error(s)
```

The completed packet contains those actual transcripts. A subsequent pass
completed docs/tracker/Ruff but git diff --check rejected four trailing-padding
lines copied from Node's coverage stdout. Only display padding is removed;
test output values and code are unchanged. The staged-file check also caught a
trailing blank line in the new ADR-0232 before its commit; that formatting was
removed. These checks stop before commit and are not model-review retries.
The fresh full record result above, not an ignored failure, owns validation.

## Unchanged source and limits

Production, scripts and all UI tests/assets are unchanged from AR-172's
dec1bc512462285cf4d43742c3e666e6d776186e candidate. This Git comparison returns
zero with empty stdout:

```bash
git diff --exit-code dec1bc512462285cf4d43742c3e666e6d776186e HEAD -- agency_runtime scripts tests/dashboard_ui.test.mjs
git diff --exit-code 9effff3f6c4f4fbe59de8793df074a041e64dab9 HEAD -- 'agency_runtime/**/*.py' 'scripts/*.py'
```

AR-172's routing evaluation and AR-165's 184/184 curated Python conformance
remain earlier unchanged-source evidence, not new staffing measurements.
No exhaustive corpus/coverage/matrix, native Windows, host activation, disk-log
retention or assembled-release claim. The fresh loopback tests validate this
specific diagnostic response-to-log boundary and absence of turn writes.
