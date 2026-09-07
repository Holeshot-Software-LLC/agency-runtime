---
title: "AR-157 current public HTTP disconnect evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [http, observability, verification, acceptance]
related:
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/decisions/0017-sanitized-server-error-boundary.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-157 public HTTP disconnect evidence

## Source and current contract

Reviewed main 6b4650b3 (PR #708), merge ledger 2329a3a3. Existing 12640d0
implementation remains present; no product or script changes.

Both public dispatch methods first recognize expected response disconnects,
close the connection and mark degraded/client_disconnected without logging
an application fault or attempting a second response. Their active observation
wrappers also catch a disconnect from the one defensive 500 attempt. The outer
handler covers pre-dispatch I/O; unrelated OS errors propagate.

The dashboard inherits the public helper and observation wrapper; there is
one classifier in http_transport.py for built-in exceptions, POSIX errno and
Winsock attributes. Synthetic code representations tested on Linux are not
native Windows execution.

Genuine application errors retain one sanitized log (method, normalized
operation, exception type and bounded frame references, not message/content)
and one fixed internal-server-error response. Real authenticated loopback
GET/POST tests verify the 500 body and absence of the private error marker.

## Direct observation proof

The primary GET/POST tests now enter do_GET/do_POST and the actual
RuntimeBoundary/observation logger rather than bypassing the boundary. Private
query, JSON body and disconnect-message sentinels stay out of all captured logs.
Each exact HTTP operation emits one degraded/client_disconnected observation
with a request ID, closes its connection and never logs an application fault
or retries a response. Defensive-500 cases separately capture the same degraded
outcome after one genuine-failure log and exactly one abandoned error write.

## Initial failures and fixture repairs

The initial four-module run had 102 passed, two failed and three existing skips
(22.62s), with full classifier statement/branch coverage. Both failures reproduce
on untouched main 6b4650b3 (two failed, 3.01s):

- test_preflight_returns_routing_and_context expected an obsolete fixed roster
  count of 14; current catalog reconciliation returns 22. The repaired assertion
  compares the response to the actual enabled Store catalog and verifies the
  fixture's code-reviewer is present, without fixing another transient count.
- test_finalize_rejects_resident_steward_as_delegated_worker expected suggestions
  from an obsolete mocked hiring flow. The test now seeds exactly one correlated
  suggestion via the real Store API, asserts insertion, submits the prohibited
  resident worker and requires the exact prior rows unchanged after HTTP 400.
  Parent-only rejection and absence of a resident-worker row remain mandatory.

These are fixture repairs, not production fallback or relaxed admission.
No skips, xfails, new authorization or threshold reductions were introduced.
AR-176 records them as repaired here, not as additional unresolved cases.

## Fresh focused verification

The two disconnect modules first passed 26 tests (0.52s). With the two repaired
HTTP cases, 28 pass (1.83s); Ruff check and format pass.

```bash
PYTHONPATH=. python -m pytest tests/test_http_server.py \
  tests/test_http_disconnects.py tests/test_dashboard_disconnects.py \
  tests/test_runtime_observability.py -q -W error \
  --cov=agency_runtime.server.http_transport --cov-branch --cov-report=term-missing
```

Final complete four-module run: 104 passed, three existing inference-flow skips,
zero failures/deselections, 22.25s. Shared transport module: 11 statements,
zero misses, four branches, zero partial branches, 100.00 percent. This is
targeted-module coverage, not aggregate Python coverage. The live server tests
use authenticated loopback, private temporary Stores and provider stubs.

## Exact-byte reuse

```bash
git diff --exit-code dccb4e85 -- agency_runtime scripts
git diff --exit-code dccb4e85 -- tests ':!tests/test_http_disconnects.py' ':!tests/test_http_server.py'
```

Both return zero. Neither changed test module belongs to the named 29-module
production spine. Therefore the [AR-156 fresh checks](AR-156-verification-workflow-20260907.md#fresh-verification)
bind unchanged runtime/scripts/spine tests: 1085 passed, three existing skips,
68.41s. The same receipt supplies unchanged 188 UI passes and production
coverage 96.93/86.71/95.71. These are explicit same-byte reuse, not new runs.

The [exact dccb4e85 wheel receipt](AR-156-verification-workflow-20260907.md#exact-packaged-browser-check)
also binds unchanged installed bytes: ten matching served assets, 21 loaded
browser checks and all three polling/fault-recovery interactions. No wheel was
rebuilt or host reinstalled for this test/documentation-only package.

## Reconciled gate and limits

ADR-0105 replaces only the obsolete sixth release-gate interpretation with
focused HTTP/observability, targeted coverage and the named warning-strict
spine. The first five criteria and original sixth wording remain in the issue.
Aggregate coverage's configured 97-percent floor is unchanged; exhaustive
corpus, matrix and native Windows were not run. No provider-staffing, hosted CI
or normal-session hook-activation claim is made. Six isolated verdicts are
required before marking done; this document supplies builder evidence only.
