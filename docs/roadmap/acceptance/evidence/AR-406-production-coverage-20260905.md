---
title: "AR-406 production coverage and AR-152 listener evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, coverage, dashboard, lifecycle]
related:
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/roadmap/acceptance/evidence/AR-323-current-schema-verification-20260905.md
supersedes: []
superseded_by: null
---

# AR-406 production coverage and AR-152 listener evidence

## Measurement diagnosis

The original Node v22.23.2 command passed 138 tests but failed the 93 percent
function floor at 91.12. Its report included the UI test file as well as product
modules. Raw V8 data had 704 test-function entries, 86 unexecuted, including
unused fixture callbacks. This is the wrong denominator for product coverage.

The product-wide recursive inclusion selector reports the seven shipped modules
listed below. No production file, function or coverage counter is excluded or
ignored; neither UI source nor tests/dashboard_ui.test.mjs changed. ADR-0220
records this explicit measurement correction, not a claim of increased coverage.

## Current coverage verification

Invoke the actual configured local Gate.command from scripts/run_local_gates.py:

```text
node --test --experimental-test-coverage \
  --test-coverage-include=agency_runtime/dashboard/**/*.js \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
tests 138; pass 138; fail 0; skipped 0; exit 0
```

The selector is one literal argv item (quoted when entered in a shell).
Measured modules: app.js, charts.js, dashboard-actions.js, dashboard-config.js,
dashboard-core.js, dashboard-live.js, dashboard-render.js. The Node report
contains all seven and omits the test fixture file. Aggregate lines 96.92 percent,
branches 86.62 percent, functions 95.71 percent; floors stay 95/86/93.

## Command-contract verification

The two parametrized local/hosted command regressions first failed because
neither command supplied the production selector: 2 failed in 1.67s.
After updating both commands, the complete four-file workflow-contract package
passes 163 tests in 5.18s, warnings strict:

```text
python -m pytest tests/test_release_packaging.py tests/test_ci_change_scope.py \
  tests/test_ci_sharding.py tests/test_ci_session_pair.py -q -W error --tb=short
163 passed in 5.18s
```

The exact-argv assertions reject narrower include patterns, any exclusions,
changed numerical floors, missing UI test invocation, and local/hosted drift.
Ruff and format checks pass for both changed Python files.

## Existing listener repair

AR-152 was already implemented in 6a3bdaa. Current source attaches one click
listener to the stable workforce grid. Each render replaces its children with
native type=button controls carrying an Inspect accessible name and worker slug;
there is no per-card listener or captured card in the disposer list. Native
button activation uses the same click path for pointer and keyboard activation.

The unchanged 50-render regression asserts exactly one grid listener and no
card-owned listeners, selects a worker through a nested label, checks the exact
request and selected detail, and verifies zero grid listeners after teardown.
The shared disposer drains its list; destroy guards against repeat disposal.
The unchanged lifecycle test verifies one successful destroy, a false second
destroy, cleared listeners, canceled confirmation, and an aborted mutation.
All these tests pass inside the same 138-case coverage invocation.

## Scope and limits

This package changes test measurement, not UI behavior, production schema or
staffing. A fresh named spine passes 1030 tests with three existing skips in
64.98s; it uses the exact PRODUCTION_SPINE tuple in scripts/run_local_gates.py.
The source-identical protected conformance baseline and all 182 mutations pass.
No new native browser, screen-reader, Windows, release-artifact, or host canary
result is claimed. No exhaustive workflow was dispatched. The existing listener
criteria are unchanged; coverage is interpreted through explicit ADR-0220 scope.

## Baseline comparison

Actual Git object comparison of merged baseline
cb7dca7733a8e1a3ff78791bf5e372dae64dafa4 and implementation candidate
12a62393613452fb322697b4cde48d8c74949422:

| Object | Baseline | Candidate |
|---|---|---|
| Entire agency_runtime tree | cd002d40de2f2e552f13705548a0272294bcac7d | cd002d40de2f2e552f13705548a0272294bcac7d |
| tests/dashboard_ui.test.mjs blob | c5afaa37778f3365d1d2a5a83a21eede35014978 | c5afaa37778f3365d1d2a5a83a21eede35014978 |

`git diff --exit-code cb7dca7733a8e1a3ff78791bf5e372dae64dafa4
12a62393613452fb322697b4cde48d8c74949422 -- agency_runtime
tests/dashboard_ui.test.mjs` exits 0 with no output. Thus both production source
and the entire behavioral test file are byte-identical, not merely described as
unchanged. The complete 138-case UI invocation above passes on these same bytes.

The first isolated AR-406 pass satisfied criteria 1/2 and reported criterion 3
absent because its excerpts showed policy intent but lacked this baseline
comparison. Preserve that result in Git, add this exact evidence, then re-freeze
AR-406 for a second verification pass. No criterion or implementation changes.
