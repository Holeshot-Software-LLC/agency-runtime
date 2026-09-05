---
title: "AR-149 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, dashboard]
related:
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/acceptance/evidence/AR-149-current-request-identity-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-149
candidate_commit: b9d68e5d872046fcb207f5318d323eb63becb601
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-149 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Real persistent HTTPConnection uses the same socket for two requests and receives distinct IDs` | 2026-09-05 | `tests/test_dashboard.py:1744-1800` |
| 1 | file | `Request dispatch clears cached identity and previous headers` | 2026-09-05 | `agency_runtime/server/dashboard.py:1308-1321` |
| 2 | test | `Each request ID is observed at matching dashboard and Store boundaries` | 2026-09-05 | `tests/test_dashboard.py:1744-1800` |
| 2 | file | `GET and protocol-error paths retain one RuntimeBoundary identity for each request` | 2026-09-05 | `agency_runtime/server/dashboard.py:1323-1370` |
| 2 | file | `All nested RuntimeBoundary instances inherit the active request ContextVar and restore it on exit` | 2026-09-05 | `agency_runtime/core/observability.py:165-271` |
| 2 | file | `Store observations take their ID from that same active request context` | 2026-09-05 | `agency_runtime/core/observability.py:300-330` |
| 2 | test | `Runtime and Store events retain one correlation ID and reset context after exit` | 2026-09-05 | `tests/test_runtime_observability.py:89-123` |
| 3 | test | `Content-free response headers and normal observations correlate; invalid supplied identities are not reflected` | 2026-09-05 | `tests/test_dashboard.py:1696-1741` |
| 3 | test | `Keep-alive protocol error and malformed next request receive fresh correlated identity` | 2026-09-05 | `tests/test_dashboard.py:1802-1910` |
| 3 | test | `Real persistent HTTP responses match dashboard and Store instrumentation request IDs` | 2026-09-05 | `tests/test_dashboard.py:1744-1800` |
| 3 | file | `JSON response headers and error outcomes use the handler's cached request identity` | 2026-09-05 | `agency_runtime/server/dashboard.py:1636-1686` |
| 3 | file | `Handler caches one identity per request and protocol errors enter its RuntimeBoundary` | 2026-09-05 | `agency_runtime/server/dashboard.py:1275-1291` |
| 3 | file | `Protocol-error and ordinary GET handlers enter the same correlation mechanism` | 2026-09-05 | `agency_runtime/server/dashboard.py:1323-1370` |
| 3 | file | `Store instrumentation emits from the request ContextVar rather than an independent ID` | 2026-09-05 | `agency_runtime/core/observability.py:300-330` |
| 3 | file | `All observed SQLite success/error paths use the shared Store emitter` | 2026-09-05 | `agency_runtime/core/store/observed_sqlite.py:50-117` |
| 4 | command-output | `Four real HTTP regressions and 180 dashboard/disconnect tests pass on current source` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-149-current-request-identity-20260905.md:28-50` |
| 4 | command-output | `Source-identical accepted installed runtime retains named spine and exact verification limitations` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md:112-128` |
| 4 | file | `Accepted bounded-delivery decision makes the exhaustive corpus optional, not a per-issue completion prerequisite` | 2026-09-05 | `docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md:40-64` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-149.1-20260905-d30bfbf2` | `0377f896ff2cb185c344bf5dcef1f98c601e3e494deaa2a7034c293f4fbfb2b4` | 2026-09-05 | tests/test_dashboard.py:1744-1800 asserts distinct response request IDs across two requests using the same socket, and dashboard.py:1308-1321 clears cached identity before each request. |
| 4 | satisfied | `AR-149.4-20260905-2ed7b6b0` | `2594c0abeeab69b991ae507bdaecb9f715ce54a80d6d9f454c9a737da45baa8a` | 2026-09-05 | AR-149 evidence records 180 passing dashboard/disconnect tests and source identity with the installed runtime; AR-271 evidence records 1030 passing named spine tests; ADR-0105 explicitly makes exhaustive checks optional. |
| 2 | satisfied | `AR-149.2-20260905-846efe09` | `8219ed8bb3b645f2cee6402552ab321ad249959a937f9441b4367a315a68bf33` | 2026-09-05 | observability.py:165-271 and 300-330 propagate the active request ID through runtime and Store boundaries; tests/test_dashboard.py:1744-1800 and tests/test_runtime_observability.py:89-123 verify matching IDs. |
| 3 | satisfied | `AR-149.3-20260905-3b6a57ee` | `b5f1c8a497b27503d008748a707d08276ac46f266671ba13c4f17b41fe41664b` | 2026-09-05 | dashboard.py shares cached identities between headers and error boundaries, observability.py propagates request context to Store emissions, and tests/test_dashboard.py asserts matching IDs across persistent requests and protocol errors. |

## Prior verification and bounded follow-up

Commit f2e41b89 preserves the first absent verdicts for criteria 2 and 3 with
their exact run IDs, digests, and reasons. Their initial excerpts omitted the
existing ContextVar inheritance and Store propagation code; the criterion-3
packet also omitted the real HTTP Store-correlation test. Those sources were
added from the same candidate without altering any criterion or product
behavior. The targeted second checks satisfied criteria 2 and 3. Criteria 1 and
4 retain their first verdicts; the current record has four satisfied criteria.
