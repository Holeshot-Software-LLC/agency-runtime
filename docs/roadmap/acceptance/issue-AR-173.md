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
candidate_commit: 594bc4d3939d144440ae52f5acdf5f840c79f25e
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

All five criteria satisfy at 594bc4d3939d144440ae52f5acdf5f840c79f25e in the
second/final review. First verdicts remain at 941b9025 before ADR-0232's explicit
representation correction. No copied verdicts or third review.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-173.1-20260907-f8cf0256` | `424913bd9ccf95cfb5d671b9347c002c21907e69747c690dbf171bb5d002d5a5` | 2026-09-07 | dashboard.py:2720-2797 validates and bypasses before allocating one UUIDv4 ahead of explain_route; test_dashboard.py:3850-3986 verifies fresh pre-call traces and no allocation for invalid or disabled requests, with two passing tests in the focused transcript. |
| 2 | satisfied | `AR-173.2-20260907-d1de4de8` | `17f8c0edfa290386ea9b29471bd39cfe2551f281e0e64ea4da9a92b8ac210baf` | 2026-09-07 | dashboard.py and observability.py bind the allocated trace to the active HTTP digest; test_dashboard.py asserts the receipt trace, exact domain-separated digest equality, and separate request ID, with a passing focused HTTP transcript. |
| 3 | satisfied | `AR-173.3-20260907-97893c7c` | `af18fd86dbee190aeaaa77fe2b782361d9c47ce86705cab589f8ec421c494d4c` | 2026-09-07 | observability.py enforces bounded metadata fields and digest-only correlation serialization; test_dashboard.py verifies records under 512 bytes exclude private values, and the cited focused transcript reports 195 passing tests. |
| 4 | satisfied | `AR-173.4-20260907-f63a37e6` | `b03892c269f4c6a27a2a06ca35ec6145dceaef1313e1ab33cca2afc965850df2` | 2026-09-07 | tests/test_dashboard.py:3850-3922 uses authenticated POST requests, asserts emitted digest equality with the response trace digest, and checks no durable turn/routing rows; lines 292-313 match observations by request ID, and the focused transcript reports passing tests. |
| 5 | satisfied | `AR-173.5-20260907-1411e758` | `4b7b62f20fd6860895e08606730dd848219e58a297526d492efe3f877f7fed5a` | 2026-09-07 | AR-173-route-lab-correlation-20260907.md transcripts show 195 focused tests and 204 UI tests passing, coverage above 95/86/93 floors, 1085 production-spine passes with three existing skips, and successful metadata, policy, worklog, docs/tracker, Ruff and diff checks. |
