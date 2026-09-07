---
title: "AR-145 focused instrumented contract review"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, testing, coverage, evidence]
related:
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0224-retire-duplicate-mandatory-coverage-checklist.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/acceptance/evidence/AR-140-current-performance-20260907.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-145 focused instrumented contract review

## Disposition

Retire the duplicate mandatory-release checklist under ADR-0224, not as an
accepted 97-percent pass. AR-176 retains actual fixture and requested aggregate
diagnostic work. Original criteria, failures and implementation history remain.

Product source: 7afa4b4d7c6aabef572b3671784894fe54181311; review ledger:
826dc593 (only the preceding PR #701 delivery record differs). Python 3.12.3,
Linux x86-64, coverage.py 7.15.0 with branch recording. No product, test,
coverage configuration or workflow changes.

## Current implementation

- `tests/test_dashboard.py:287` waits for the observation carrying the exact
  request ID. An HTTP response arriving before its background log no longer
  acts as evidence that the log is missing.
- `tests/test_preflight_bounds.py:995` pre-seeds the specialist and observes
  persisted started/reused-in-progress ownership before releasing the route.
  Both owner-success and owner-failure cases remain exercised.
- `tests/test_selector_coverage_complete_basics.py:909` supplies shaped
  microbenchmark, semantic-scale and CLI-startup results while exercising real
  accuracy/report assembly. Its instrumentation path invokes no real wall-clock
  performance gates.
- `tests/test_release_coverage_authority_boundaries.py` retains validation,
  transaction rollback, missing receipt, SQLite observation, pagination and
  current MCP admission cases. The deleted delegate-tool tests were separately
  retired at 047ce723, not restored to inflate coverage.

## Instrumented result

One bounded invocation, no retry, exited zero: **41 passed in 12.08s**.

```bash
PYTHONPATH=. COVERAGE_FILE=<private-temporary-directory>/.coverage \
python -m coverage run --branch --source=agency_runtime -m pytest \
  tests/test_dashboard.py::test_dashboard_correlates_requests_with_content_free_observations \
  tests/test_preflight_bounds.py::test_concurrent_duplicate_preflights_share_one_owner_and_one_outcome \
  tests/test_selector_coverage_complete_basics.py::test_routing_eval_exercises_accuracy_gates_with_synthetic_performance \
  tests/test_release_coverage_authority_boundaries.py -q -W error
```

The actual temporary namespace was a newly created private directory; no shared
coverage result or user database was overwritten. This records branch execution
for these cases only. No aggregate report was requested, no minimum was lowered
and no claim of 97-percent repository coverage is made. A single focused run
also does not prove every possible concurrent schedule or serial corpus order.

The existing `pyproject.toml` source is `agency_runtime` with branches enabled.
The manual workflow still combines the four shards and runs
`python -m coverage report --fail-under=97`. Nothing here changes that contract.

AR-140's same-product-source standalone routing report already passed all 39
versioned recall/performance/startup gates without coverage. It is reused only
as that scoped report, not a fresh complete performance-suite or native-host
run. The prior named spine/UI/conformance evidence remains separately scoped.
No exhaustive suite, hosted dispatch, native Windows or live provider call ran.

## Remaining owner

AR-176 owns the six known stale fixtures and any reproduced branch gaps in an
explicitly requested aggregate diagnostic. AR-145 is not a second mandatory
release gate. The broader backlog and current ordinary-session activation
remain unfinished; no acceptance verdict or tracker closure is fabricated.
