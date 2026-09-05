---
title: "Measure dashboard coverage over production modules"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [testing, dashboard, coverage, measurement]
related:
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/issue-AR-152-bound-dashboard-live-listeners.md
  - scripts/run_local_gates.py
  - .github/workflows/ci.yml
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0220
type: decision
deciders: [maintainers]
---

# ADR-0220: Measure dashboard coverage over production modules

## Context

The owner requested that backlog requirements be judged for current relevance,
including badly scoped agent-authored proposals. AR-406 initially interpreted
91.12 percent aggregate function coverage as missing product callback tests.
The exact Node report also includes tests/dashboard_ui.test.mjs; raw V8 output
contains 704 function entries there, 86 unexecuted. Test doubles and unused
fixture callbacks are therefore changing a product-quality score.

The same 138 passing tests measure all seven shipped dashboard JavaScript
modules at 96.92 percent lines, 86.62 percent branches, and 95.71 percent
functions, above the unchanged 95/86/93 floors. This is a measurement-scope
error, not a reason to alter working behavior or exercise unused test stubs.

## Decision

Both local and hosted dashboard gates measure
`agency_runtime/dashboard/**/*.js` through Node's explicit coverage inclusion
selector. It includes every current production JavaScript module and future
nested JavaScript modules; the test file still runs completely but is not part
of the product coverage denominator.

- Retain all existing numeric floors: 95 lines, 86 branches, 93 functions.
- Retain every UI behavioral test, including errors, accessibility and lifecycle
  cleanup. No product file or function is excluded, skipped, or instrumented away.
- Pin identical complete local/CI command arguments in regression tests, so a
  narrower file list, exclusion, or lowered floor fails the workflow contract.
- Preserve both the original mixed-scope failure and corrected product-scope
  result. They measure different denominators; do not claim a coverage increase
  or a behavioral fix.

## Consequences

The gate reflects exercised product code rather than fixture implementation
details. A product regression can still fail a test or the unchanged floors.
Coverage remains a scoped aggregate, not proof of every interaction or a native
browser session. Adding a new production script extension would require an
explicit measurement-contract update; no such change is part of this package.

## Alternatives

- Add calls to unused test stubs: does not improve product behavior evidence.
- Lower the function floor: unnecessary; all production floors already pass.
- Exclude a poorly covered production module: rejected; all seven remain in scope.
- Keep fixtures in the product score: continues unrelated denominator drift.
