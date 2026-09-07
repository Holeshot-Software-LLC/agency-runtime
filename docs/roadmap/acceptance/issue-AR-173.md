---
title: "AR-173 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, dashboard, correlation]
related:
  - docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-173
candidate_commit: pending
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
| 1 | file | Explicit reconciliation distinguishes request IDs, diagnostic traces and disabled bypass | 2026-09-07 | docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md#decision |
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
| 4 | file | Explicit criterion reconciliation preserves the original wording | 2026-09-07 | docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md#decision |
| 5 | file | Bounded verification requirement is explicit before acceptance | 2026-09-07 | docs/decisions/0232-represent-route-lab-observations-by-trace-digest.md#decision |
| 5 | command-output | Actual full dashboard/explanation/observability command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#full-focused-transcript |
| 5 | command-output | Actual complete UI coverage command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#full-ui-and-coverage-transcript |
| 5 | command-output | Actual fresh named-spine command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#production-spine-transcript |
| 5 | command-output | Actual metadata/policy/worklog/strict docs/tracker/Ruff/diff results | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md#record-checks |

## Verification

First verdicts are preserved at 941b9025. Pending one second/final all-criteria
review after ADR-0232's explicit representation correction. No copied verdicts.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
