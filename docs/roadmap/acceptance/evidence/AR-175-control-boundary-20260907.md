---
title: "AR-175 control failure boundary evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, dashboard, correlation, compatibility, backlog]
related:
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/dashboard/dashboard-core.js
  - agency_runtime/dashboard/dashboard-live.js
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
---

# AR-175: Atomic control failure boundary

## Scope and finding

Linux/Python 3.12.3/Node 22.23.2 after clean 7f403ab7 (PR #723 plus merge ledger).
The legacy reconstruction path is already removed. A real remaining defect in
the same failure boundary drops request IDs when successful HTTP responses
contain missing/wrong schema, null payload, or malformed JSON. HTTP 404 and
network failures already retain IDs; abort and obsolete-generation paths
already remain quiet. The issue's claim of correlated failure was too broad.

Twenty new table-driven browser-DOM cases cover both control-only and full
refresh paths, ten failure/cancellation shapes each. Before the fix, eight
schema-failure cases fail because errorRequestId is empty; twelve pass.
The implementation moves schema validation into the existing API validation
callback, preserving its safe request ID. The refresh owners still suppress
aborted, suspended and superseded work; no compatibility fallback is added.

This is a scoped control failure repair, not completion of AR-170's remaining
collection-call-site/gate-receipt obligations. No owner profile, native host
installation, provider credential or Windows execution is changed.

## Red reproduction

```bash
node --test --test-reporter=spec --test-name-pattern='control boundary' tests/dashboard_ui.test.mjs
```

Complete stdout/stderr, exit one, before the production fix; file-URI scheme
prefixes are stripped from stack paths for the repository documentation policy.
The first draft record check rejected those prefixes; this display-only
normalization changes no test outcome, assertion, path or line number:

```text
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed with HTTP 404.
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed before response.
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed with HTTP 404.
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed before response.
✔ control boundary refreshControlPlane preserves state without legacy fanout (missing-endpoint) (4.163284ms)
✖ control boundary refreshControlPlane preserves state without legacy fanout (missing-schema) (0.834144ms)
✖ control boundary refreshControlPlane preserves state without legacy fanout (wrong-schema) (0.513075ms)
✖ control boundary refreshControlPlane preserves state without legacy fanout (null-payload) (0.368009ms)
✖ control boundary refreshControlPlane preserves state without legacy fanout (malformed-json) (0.568012ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (network) (0.454036ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (abort) (0.403568ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (aborted-invalid) (0.434647ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (suspended-invalid) (0.617561ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (obsolete-invalid) (0.401738ms)
✔ control boundary refreshAll preserves state without legacy fanout (missing-endpoint) (8.58616ms)
✖ control boundary refreshAll preserves state without legacy fanout (missing-schema) (0.530413ms)
✖ control boundary refreshAll preserves state without legacy fanout (wrong-schema) (1.393077ms)
✖ control boundary refreshAll preserves state without legacy fanout (null-payload) (0.416267ms)
✖ control boundary refreshAll preserves state without legacy fanout (malformed-json) (0.459486ms)
✔ control boundary refreshAll preserves state without legacy fanout (network) (0.374599ms)
✔ control boundary refreshAll preserves state without legacy fanout (abort) (0.32774ms)
✔ control boundary refreshAll preserves state without legacy fanout (aborted-invalid) (0.281491ms)
✔ control boundary refreshAll preserves state without legacy fanout (suspended-invalid) (0.370849ms)
✔ control boundary refreshAll preserves state without legacy fanout (obsolete-invalid) (0.268572ms)
ℹ tests 20
ℹ suites 0
ℹ pass 12
ℹ fail 8
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 90.349807

✖ failing tests:

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshControlPlane preserves state without legacy fanout (missing-schema) (0.834144ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshControlPlane preserves state without legacy fanout (wrong-schema) (0.513075ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshControlPlane preserves state without legacy fanout (null-payload) (0.368009ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshControlPlane preserves state without legacy fanout (malformed-json) (0.568012ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshAll preserves state without legacy fanout (missing-schema) (0.530413ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshAll preserves state without legacy fanout (wrong-schema) (1.393077ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshAll preserves state without legacy fanout (null-payload) (0.416267ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }

test at tests/dashboard_ui.test.mjs:4682:5
✖ control boundary refreshAll preserves state without legacy fanout (malformed-json) (0.459486ms)
  AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
  + actual - expected

  + ''
  - '00000000-0000-4000-8000-000000000001'

      at TestContext.<anonymous> (/tmp/agency-runtime-ar175-reconciliation/tests/dashboard_ui.test.mjs:4746:16)
      at async Test.run (node:internal/test_runner/test:1054:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:744:7) {
    generatedMessage: true,
    code: 'ERR_ASSERTION',
    actual: '',
    expected: '00000000-0000-4000-8000-000000000001',
    operator: 'strictEqual',
    diff: 'simple'
  }
```


## Focused green transcript

Same command after the source repair, exit zero:

```bash
node --test --test-reporter=spec --test-name-pattern='control boundary' tests/dashboard_ui.test.mjs
```

```text
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed with HTTP 404.
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed before response.
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed with HTTP 404.
Agency dashboard request 00000000-0000-4000-8000-000000000001 failed before response.
✔ control boundary refreshControlPlane preserves state without legacy fanout (missing-endpoint) (4.762765ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (missing-schema) (0.524655ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (wrong-schema) (0.424787ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (null-payload) (0.32007ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (malformed-json) (0.574243ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (network) (0.356739ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (abort) (0.32803ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (aborted-invalid) (0.414788ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (suspended-invalid) (0.627981ms)
✔ control boundary refreshControlPlane preserves state without legacy fanout (obsolete-invalid) (0.445237ms)
✔ control boundary refreshAll preserves state without legacy fanout (missing-endpoint) (8.467793ms)
✔ control boundary refreshAll preserves state without legacy fanout (missing-schema) (0.411967ms)
✔ control boundary refreshAll preserves state without legacy fanout (wrong-schema) (1.223473ms)
✔ control boundary refreshAll preserves state without legacy fanout (null-payload) (0.392608ms)
✔ control boundary refreshAll preserves state without legacy fanout (malformed-json) (0.446476ms)
✔ control boundary refreshAll preserves state without legacy fanout (network) (0.376608ms)
✔ control boundary refreshAll preserves state without legacy fanout (abort) (0.32455ms)
✔ control boundary refreshAll preserves state without legacy fanout (aborted-invalid) (0.315211ms)
✔ control boundary refreshAll preserves state without legacy fanout (suspended-invalid) (0.33738ms)
✔ control boundary refreshAll preserves state without legacy fanout (obsolete-invalid) (0.286312ms)
ℹ tests 20
ℹ suites 0
ℹ pass 20
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 88.819304
```

The two refresh modes each retain baseline config, pending config, hosts,
roster, snapshots, overview and control/live revisions. Exact request lists
allow only /api/control (and the normal /api/live initial full-refresh call);
any legacy fallback fails. Visible failures contain the exact sent request ID.
All eight cancellation/lifecycle/generation cases preserve the notice and
fresh-state flag. Both in-flight flags are cleared.

## Asset gate

Actual commands and output, exit zero:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_release_packaging.py -k 'release_resources_are_addressable or dashboard_coverage_gates' -q -W error
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -c 'from importlib.resources import files; names=("index.html", "app.css", "charts.js", "app.js", "dashboard-actions.js", "dashboard-config.js", "dashboard-core.js", "dashboard-live.js", "dashboard-render.js", "package.json"); total=sum(len(files("agency_runtime").joinpath("dashboard", name).read_bytes()) for name in names); print(f"dashboard_bytes={total} strict_ceiling={378*1024} headroom={378*1024-total}")'
```

```text
....                                                                     [100%]
4 passed, 186 deselected in 0.22s
dashboard_bytes=386965 strict_ceiling=387072 headroom=107
```

The unchanged current strict ceiling is 378 KiB. Relative to parent main's
387,039 bytes, the repair saves 74 bytes. The older issue's 257,620-byte total
and 5,547-byte headroom are dated July 27 observations, not current totals.
No asset-floor test, release budget or production behavior is removed.

## Full UI and current coverage transcript

```bash
set -o pipefail
node --test --experimental-test-coverage '--test-coverage-include=agency_runtime/dashboard/**/*.js' --test-coverage-lines=95 --test-coverage-branches=86 --test-coverage-functions=93 tests/dashboard_ui.test.mjs | tail -28
```

Actual final 28 lines, exit zero, with display-only trailing padding removed:

```text
  type: 'test'
  ...
1..220
# tests 224
# suites 0
# pass 224
# fail 0
# cancelled 0
# skipped 0
# todo 0
# duration_ms 250.156288
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
#   dashboard-live.js    |  95.34 |    87.38 |   98.77 | 63-64 242-244 276-277 360-363 372-373 676 750-751 798-831 852-854 863 875 903-904 938 1229-1230 1237-1238 1354-1355 1362 1441-1442 1627-1628 1767-1769 1784-1787 1796-1799 1893 1924-1925 1938-1940 1964-1966 1969-1970 2044-2045 2047-2048 2059-2060 2214 2247 2355-2363 2377-2381 2389-2390 2399-2400 2430-2431
#   dashboard-render.js  |  97.96 |    86.25 |   97.01 | 120-128 777-782 896-897 933-935 1458 1461-1462 1494-1495 1654-1655 1923-1928 2323-2340
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# all files              |  96.93 |    86.78 |   95.74 |
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# end of coverage report
```


## Initial checkpoint

The focused regression, complete UI/current coverage, actual asset gate,
Ruff and strict documentation/diff checks precede the first clean source
checkpoint. The fresh named spine passes 1085/three existing skips in 69.72s;
private source-served browser
proof and isolated acceptance remain pending. No completed browser or native
host claim is made here.

Only obsolete criterion 6 is reconciled under existing ADR-0105, with original
wording preserved. Criteria 1–5 stay unchanged. No new architectural policy.


## Production spine transcript

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_storage_file_trust.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_upstream_selection_eval.py tests/test_decision_conformance.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_owner_authority.py tests/test_security_turn_boundaries.py tests/test_canary_coverage_complete.py tests/test_complexity_refactors.py tests/test_coverage_final_host_cli.py tests/test_resident_manager_lifecycle.py -q -W error
```

Actual stdout, exit zero:

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
1085 passed, 3 skipped in 69.72s (0:01:09)
```

## Installed artifact identity

Built from clean source/ledger checkpoint
a96483ad93c3023b47e7de016095ac20b6e31393 (the dashboard repair is 96f6b49b).
The optional browser driver was then expanded to include HTTP 404 and network
faults for both refresh methods; no packaged runtime or dashboard bytes changed
between the two browser runs. Later acceptance/documentation commits do not
claim rebuilt artifacts.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m scripts.build_distributions /tmp/agency-ar175-browser.PrWwR8/dist --expected-commit a96483ad93c3023b47e7de016095ac20b6e31393
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_distribution.py /tmp/agency-ar175-browser.PrWwR8/dist --expected-commit a96483ad93c3023b47e7de016095ac20b6e31393 --artifact-set portable
/tmp/agency-ar404-venv.AUBJlC/bin/python -m twine check --strict /tmp/agency-ar175-browser.PrWwR8/dist/agency_runtime-0.1.0-py3-none-any.whl /tmp/agency-ar175-browser.PrWwR8/dist/agency_runtime-0.1.0.tar.gz
/tmp/agency-ar404-venv.AUBJlC/bin/python -m pip install --no-deps --target /tmp/agency-ar175-browser.PrWwR8/wheel /tmp/agency-ar175-browser.PrWwR8/dist/agency_runtime-0.1.0-py3-none-any.whl
```

Actual outputs (all exit zero; Twine's line wrapping compacted):
```text
Canonical distribution build passed: agency_runtime-0.1.0-py3-none-any.whl, agency_runtime-0.1.0.tar.gz
Distribution verification passed (artifact contents match release policy).
Checking /tmp/agency-ar175-browser.PrWwR8/dist/agency_runtime-0.1.0-py3-none-any.whl: PASSED
Checking /tmp/agency-ar175-browser.PrWwR8/dist/agency_runtime-0.1.0.tar.gz: PASSED
Successfully installed agency-runtime-0.1.0
```

SHA-256:
- Wheel: `9ba064363169c978a9968a4575f273b8ad45cb2b0bbf3d49d7f6560d939b4d3d`.
- Sdist: `59668dec6e3b4ea8b3fe567ab8fc9cc71812ce4123590ef6ff35669a2fe5f840`.

Dependencies are reused from the isolated development venv, not asserted to
have been independently installed. This is private installed-wheel browser QA,
not a publication, Windows artifact, normal-profile or native-host canary.

## Loaded browser verification

The reusable Python driver requires the exact installed package parent, creates
a private five-agent Store, authenticates the real HTTP server, stubs native
host inventory, and denies Python server outbound connections. Chromium's
sandbox stays enabled. Faults alter real HTTP responses only after checking the
real server's v1 schema and matching correlation header; network faults abort
before any response. No owner profile, provider or native host is exercised.

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python scripts/context_handoff_status.py --json --threshold 50
env PYTHONPATH=/tmp/agency-ar175-browser.PrWwR8/wheel /tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_dashboard_browser.py --tools /tmp/agency-ar138-browser.uQUVCv --package-root /tmp/agency-ar175-browser.PrWwR8/wheel --output /tmp/agency-ar175-browser.PrWwR8/browser-expanded --browser /snap/bin/chromium
```

Immediately preceding telemetry was 60.9 percent remaining; no checkpoint was
required. The earlier 24-schema-fault run also passed; this expanded run adds
404 and network cases. Both refresh methods run all six faults at all three
widths (1280/1024/375). Every case asserts full last-good state retention,
visible stale failure with the actual sent ID, no legacy GETs and successful
live-server recovery. The independent lifecycle/obsolete races remain in the
20 deterministic cases, not mislabeled as browser timing measurements.

Actual expanded-run stdout, exit zero:
```text
{"width":1280,"view":"overview","violations":[],"clippedMetrics":[]}
{"width":1280,"view":"routing","violations":[],"clippedMetrics":[]}
{"width":1280,"view":"evidence","violations":[],"clippedMetrics":[]}
{"width":1280,"view":"roster","violations":[],"clippedMetrics":[]}
{"width":1280,"view":"workforce","violations":[],"clippedMetrics":[]}
{"width":1280,"view":"hosts","violations":[],"clippedMetrics":[]}
{"width":1280,"view":"settings","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"overview","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"routing","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"evidence","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"roster","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"workforce","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"hosts","violations":[],"clippedMetrics":[]}
{"width":1024,"view":"settings","violations":[],"clippedMetrics":[]}
{"width":375,"view":"overview","violations":[],"clippedMetrics":[]}
{"width":375,"view":"routing","violations":[],"clippedMetrics":[]}
{"width":375,"view":"evidence","violations":[],"clippedMetrics":[]}
{"width":375,"view":"roster","violations":[],"clippedMetrics":[]}
{"width":375,"view":"workforce","violations":[],"clippedMetrics":[]}
{"width":375,"view":"hosts","violations":[],"clippedMetrics":[]}
{"width":375,"view":"settings","violations":[],"clippedMetrics":[]}
{"passed":true,"views":21,"interactions":[{"width":1280,"preservesDirtyFieldFocusSelectionAndDetails":true,"keyboardScrollsConfiguration":true,"failure":{"retainsRevision":true,"visibleStaleMarker":true,"requestId":"cb933986-9733-49c7-a9c1-e981adb3d2b8","consoleCorrelated":true,"recovered":true}},{"width":1024,"preservesDirtyFieldFocusSelectionAndDetails":true,"keyboardScrollsConfiguration":true,"failure":{"retainsRevision":true,"visibleStaleMarker":true,"requestId":"83b7f51a-3166-47a7-b9c5-1f0d974d8e8e","consoleCorrelated":true,"recovered":true}},{"width":375,"preservesDirtyFieldFocusSelectionAndDetails":true,"keyboardScrollsConfiguration":true,"failure":{"retainsRevision":true,"visibleStaleMarker":true,"requestId":"c43ac9c7-9c92-4a61-be15-708a557c93a8","consoleCorrelated":true,"recovered":true}}],"controlFailures":36,"postRequests":0,"failures":[],"unexpectedErrors":[]}
```

## Browser result projection

This projection is computed from the retained [raw report](AR-175-browser-20260907/report.json).
It is not a substitute for the raw per-case IDs, viewport, accessibility and
interaction results. Screenshot inspection covered the actual stale notices in
[desktop](AR-175-browser-20260907/1280-control-schema.png) and
[mobile](AR-175-browser-20260907/375-control-schema.png) settings; automated text
assertions prove the exact IDs. No full accessibility certification is claimed.

```json
{
  "observed": "2026-09-07T21:04:36.419Z",
  "browser": "152.0.7977.64",
  "playwright": "1.63.0",
  "axe": "4.13.0",
  "passed": true,
  "views": 21,
  "controlFailures": 36,
  "realServerEchoes": 30,
  "networkFaultsWithoutResponse": 6,
  "uniqueFaultRequestIds": 36,
  "legacyRequests": 0,
  "postRequests": 0,
  "failures": [],
  "unexpectedErrors": []
}
```

## Served bytes and headers

The report hashes all ten installed dashboard resources. This executable
readback compares every hash with the checked source and checks uniqueness and
exact header correlation across all faults:

```bash
node --input-type=module -e 'import {readFileSync} from "node:fs"; import {createHash} from "node:crypto"; import assert from "node:assert/strict"; const r=JSON.parse(readFileSync("docs/roadmap/acceptance/evidence/AR-175-browser-20260907/report.json")); for(const [name,hash] of Object.entries(r.assets)) assert.equal(createHash("sha256").update(readFileSync("agency_runtime/dashboard/"+name)).digest("hex"),hash); assert.equal(new Set(r.controlFailures.map(x=>x.requestId)).size,36); assert.ok(r.controlFailures.every(x=>x.fault==="network" ? x.responseRequestId===null : x.responseRequestId===x.requestId)); console.log(JSON.stringify({sourceAssetHashesMatch:10,uniqueFaultRequestIds:36,realServerEchoes:30,networkFaultsWithoutResponse:6,passed:r.passed}));'
```

Actual stdout, exit zero:
```text
{"sourceAssetHashesMatch":10,"uniqueFaultRequestIds":36,"realServerEchoes":30,"networkFaultsWithoutResponse":6,"passed":true}
```

## Record checks

Before freezing the pending acceptance record, the current substantive source,
browser driver and evidence pass these strict checks. The worklog ledger is
current through its preceding checkpoint; the immediately following ledger
records this candidate.

```bash
set -e
export PYTHONPATH=.
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/docs_metadata.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_policy_availability.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/update_worklog.py --check
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_docs.py --require-tracker
/tmp/agency-ar404-venv.AUBJlC/bin/python scripts/verify_tracker.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime tests scripts
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format --check agency_runtime tests scripts
git diff --check
```

Actual stdout, exit zero:
```text
checked 1213 Markdown documents
worklog index is current (2032 commits)
documentation validation passed for 1213 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```

The exhaustive corpus, coverage shards and compatibility matrix were not
requested and did not run. This local delivery is not new hosted CI, native
Windows, credential readiness or normal-session staffing certification.

The first draft omitted the empty Verification table header; strict docs
rejected it before any isolated verifier ran. Adding the required empty table
fixed the draft shape without adding any verdict. Fresh staged-packet check:

```text
checked 1215 Markdown documents
worklog index is current (2032 commits)
documentation validation passed for 1215 Markdown files
tracker validation passed for 397 roadmap items (2 PR-tracked historical item(s) skipped)
All checks passed!
766 files already formatted
```
