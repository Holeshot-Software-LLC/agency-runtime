---
title: "AR-157 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, http, observability]
related:
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-157
candidate_commit: a35657e14e0d0bd669a542f02abda2b64a5374ca
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-157 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Public primary GET and POST catches close expected disconnects before application logging or another response | 2026-09-07 | agency_runtime/server/http.py:144-247 |
| 1 | test | GET and POST perform one primary response, close quietly and never log or attempt a 500 | 2026-09-07 | tests/test_http_disconnects.py:44-103 |
| 1 | command-output | Complete public/dashboard disconnect and real HTTP package passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#fresh-focused-verification |
| 2 | file | Guard around dispatch catches an abandoned defensive response inside its observation boundary | 2026-09-07 | agency_runtime/server/http.py:105-130 |
| 2 | test | Both public defensive-500 paths close after one application log and exactly one error response attempt | 2026-09-07 | tests/test_http_disconnects.py:141-197 |
| 2 | test | Dashboard defensive-500 disconnect shares the quiet bounded behavior | 2026-09-07 | tests/test_dashboard_disconnects.py:135-170 |
| 2 | command-output | Fresh defensive-response cases pass within the complete focused package | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#fresh-focused-verification |
| 3 | file | One classifier handles built-in disconnects, POSIX errno and Winsock attributes | 2026-09-07 | agency_runtime/server/http_transport.py:1-40 |
| 3 | file | Public close helper delegates classification to the shared function | 2026-09-07 | agency_runtime/server/http.py:105-130 |
| 3 | file | Dashboard inherits the public handler and its classifier | 2026-09-07 | agency_runtime/server/dashboard.py:1237-1243 |
| 3 | file | Dashboard outer boundary invokes the same inherited close helper | 2026-09-07 | agency_runtime/server/dashboard.py:1308-1321 |
| 3 | test | Built-in, POSIX and Winsock representations are recognized and unrelated errors rejected | 2026-09-07 | tests/test_dashboard_disconnects.py:30-71 |
| 3 | command-output | Shared classifier achieves full statement/branch coverage on Linux; native Windows is not claimed | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#fresh-focused-verification |
| 4 | test | Real primary boundary emits exact degraded/client_disconnected evidence without query, body or error sentinels | 2026-09-07 | tests/test_http_disconnects.py:52-103 |
| 4 | test | Defensive response observations retain the same exact outcome and reason for GET and POST | 2026-09-07 | tests/test_http_disconnects.py:149-197 |
| 4 | file | Observation envelope and emitter serialize metadata only | 2026-09-07 | agency_runtime/core/observability.py:106-163 |
| 4 | test | Real authenticated HTTP response correlates request identity and excludes private path content from every observation | 2026-09-07 | tests/test_http_server.py:1181-1226 |
| 4 | command-output | Primary observation and privacy assertions are exercised in the fresh passing package | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#direct-observation-proof |
| 5 | file | Application-failure logging retains bounded frame references without exception content | 2026-09-07 | agency_runtime/server/http.py:899-910 |
| 5 | test | Genuine GET/POST failures each log once and attempt one fixed sanitized 500 | 2026-09-07 | tests/test_http_disconnects.py:106-138 |
| 5 | test | Real loopback GET/POST faults return fixed 500 bodies and never leak the private exception marker | 2026-09-07 | tests/test_http_server.py:1143-1168 |
| 5 | command-output | Complete HTTP/disconnect/runtime-observation package passes warning-strict | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#fresh-focused-verification |
| 6 | command-output | 104 focused tests pass with three existing skips and 100 percent targeted transport coverage | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#fresh-focused-verification |
| 6 | command-output | Exact source/test binding reuses the unchanged named 29-module warning-strict spine and packaged checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-157-http-disconnects-20260907.md#exact-byte-reuse |
| 6 | command-output | Named spine receipt is 1085 passes and three existing skips | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md#fresh-verification |
| 6 | file | Existing delivery policy makes exhaustive coverage/corpus/matrix optional diagnostics | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |

## Verification

Pending six isolated single-criterion verifier results.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
