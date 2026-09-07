---
title: "AR-173 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, correlation]
related:
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-173
candidate_commit: f4f5124ef6433db9cae18784c15cc76ba880b391
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-173 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Validated enabled requests allocate and attach UUIDv4 before calling explanation; disabled requests return first | 2026-09-07 | agency_runtime/server/dashboard.py:2720-2797 |
| 1 | test | Two actual explanations prove fresh UUIDs and pre-call attachment; invalid task cannot allocate a trace | 2026-09-07 | tests/test_dashboard.py:3850-3937 |
| 1 | test | Disabled Route Lab cannot allocate a trace or inspect host/catalog and returns empty trace | 2026-09-07 | tests/test_dashboard.py:3940-3986 |
| 1 | file | Explicit reconciliation distinguishes request IDs, diagnostic traces and disabled bypass | 2026-09-07 | docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md#decision |
| 1 | command-output | Authenticated enabled/invalid/disabled regression transcript | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#focused-http-transcript |
| 2 | file | POST entry establishes the current request boundary and invokes the Route Lab handler | 2026-09-07 | agency_runtime/server/dashboard.py:1464-1510 |
| 2 | file | Handler attaches one UUID and passes that exact value into explanation before returning receipt | 2026-09-07 | agency_runtime/server/dashboard.py:2775-2813 |
| 2 | file | Explanation passes the supplied trace through routing and returns its receipt | 2026-09-07 | agency_runtime/core/selector/explain.py:309-340 |
| 2 | file | Observation correlation uses domain-separated SHA-256 of a bounded ID | 2026-09-07 | agency_runtime/core/observability.py:72-81 |
| 2 | file | Active observation and context are updated together | 2026-09-07 | agency_runtime/core/observability.py:221-246 |
| 2 | file | Public correlator selects the active boundary | 2026-09-07 | agency_runtime/core/observability.py:293-305 |
| 2 | test | Exact per-request response/log trace equality and fresh two-request identity | 2026-09-07 | tests/test_dashboard.py:3850-3922 |
| 2 | command-output | Real HTTP equality assertions pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#focused-http-transcript |
| 3 | file | Closed metadata-only schema and strict bounds on all values | 2026-09-07 | agency_runtime/core/observability.py:26-145 |
| 3 | file | Serialization emits only metadata in a single-line log envelope | 2026-09-07 | agency_runtime/core/observability.py:140-163 |
| 3 | test | HTTP observations have allowed keys, bounded UTF-8 length and no task/session/bearer/prompt values | 2026-09-07 | tests/test_dashboard.py:3887-3922 |
| 3 | test | Envelope schema rejects content-like labels and remains single-line | 2026-09-07 | tests/test_runtime_observability.py:31-75 |
| 3 | command-output | Full HTTP and observability suites pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#full-focused-transcript |
| 4 | test | Actual HTTP explanation response equals per-request emitted digest and creates no durable diagnostic rows | 2026-09-07 | tests/test_dashboard.py:3850-3922 |
| 4 | test | Collector selects only the exact request's dashboard envelope | 2026-09-07 | tests/test_dashboard.py:292-313 |
| 4 | file | Real POST handler supplies trace and sends resulting receipt | 2026-09-07 | agency_runtime/server/dashboard.py:2775-2813 |
| 4 | file | Explanation explicitly stays diagnostic-only | 2026-09-07 | agency_runtime/core/selector/explain.py:224-245 |
| 4 | file | Routing receives trace but no evidence Store on diagnostic path | 2026-09-07 | agency_runtime/core/selector/explain.py:309-340 |
| 4 | file | Current observation emits metadata through logger, not a turn insert | 2026-09-07 | agency_runtime/core/observability.py:140-163 |
| 4 | command-output | Fresh authenticated equality/no-persistence regression passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#focused-http-transcript |
| 4 | file | Explicit criterion reconciliation preserves the original wording | 2026-09-07 | docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md#decision |
| 5 | file | Bounded verification requirement is explicit before acceptance | 2026-09-07 | docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md#decision |
| 5 | command-output | Actual full dashboard/explanation/observability command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#full-focused-transcript |
| 5 | command-output | Actual complete UI coverage command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#full-ui-and-coverage-transcript |
| 5 | command-output | Actual fresh named-spine command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#production-spine-transcript |
| 5 | command-output | Actual metadata/policy/worklog/strict docs/tracker/Ruff/diff results | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#record-checks |

## Verification

First isolated review at f4f5124ef6433db9cae18784c15cc76ba880b391 satisfies
1/3/4/5 and contradicts 2: the response carries the raw trace, while observation
correlation is its domain-separated digest. Preserve these verdicts before
explicitly correcting that remaining original wording. No runtime defect.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-173.1-20260907-b064d007` | `482a1db78b3fa12dc7ed01bf0c8e9bc66a16b1d1f9ae0aff7754cc6716762fa4` | 2026-09-07 | dashboard.py:2720-2797 allocates one UUIDv4 after validation and enabled checks, before explain_route; test_dashboard.py:3850-3986 verifies fresh traces, pre-call attachment, and no allocation for invalid or disabled requests, with a passing focused transcript. |
| 2 | contradicted | `AR-173.2-20260907-9acef576` | `f845babb31d3c6b016e2c9b5a8686119c9c3006b015a0e6a1d634b3bbbf42b03` | 2026-09-07 | observability.py:72-81 and 221-246 show the HTTP observation carries only a SHA-256 correlation_digest, while tests/test_dashboard.py:3850-3922 shows the receipt carries the raw trace_id; they do not carry the exact same trace value. |
| 3 | satisfied | `AR-173.3-20260907-f532d39e` | `429ff8a2d0540bc57dbc41b852c284d2773dc502c5be5f675290fe45dd5179de` | 2026-09-07 | observability.py:26-163 enforces bounded metadata fields and hashed correlation IDs; test_dashboard.py:3887-3922 verifies records under 512 bytes exclude task, session, bearer token, and prompt content. |
| 4 | satisfied | `AR-173.4-20260907-ebf79a73` | `5524570bd0ebe36482cf58bbbb2e3b787adad8da00da2515d8c66f650c4e7b3c` | 2026-09-07 | tests/test_dashboard.py:3850-3922 asserts authenticated POST response-trace digest equality with the request-matched emitted observation and no durable turn/routing rows; the focused HTTP transcript records a passing run. |
| 5 | satisfied | `AR-173.5-20260907-1ec2c708` | `d068d3128888e4fab9a1b8eba8c50a9715f6b667948366a40cd14c67318b9bed` | 2026-09-07 | AR-173-route-lab-correlation-20260907.md records 195 focused tests passing, 204 UI tests passing above coverage floors, 1085 production-spine tests passing with 3 existing skips, and zero exits for metadata, policy, worklog, strict docs/tracker, Ruff and diff checks. |
