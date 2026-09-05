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
| 3 | test | `Content-free response headers and normal observations correlate; invalid supplied identities are not reflected` | 2026-09-05 | `tests/test_dashboard.py:1696-1741` |
| 3 | test | `Keep-alive protocol error and malformed next request receive fresh correlated identity` | 2026-09-05 | `tests/test_dashboard.py:1802-1910` |
| 4 | command-output | `Four real HTTP regressions and 180 dashboard/disconnect tests pass on current source` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-149-current-request-identity-20260905.md:28-50` |
| 4 | command-output | `Source-identical accepted installed runtime retains named spine and exact verification limitations` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md:112-128` |
| 4 | file | `Accepted bounded-delivery decision makes the exhaustive corpus optional, not a per-issue completion prerequisite` | 2026-09-05 | `docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md:40-64` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-149.1-20260905-d30bfbf2` | `0377f896ff2cb185c344bf5dcef1f98c601e3e494deaa2a7034c293f4fbfb2b4` | 2026-09-05 | tests/test_dashboard.py:1744-1800 asserts distinct response request IDs across two requests using the same socket, and dashboard.py:1308-1321 clears cached identity before each request. |
| 2 | absent | `AR-149.2-20260905-3837fe67` | `f21d0d6f7571bf972c80db9ba90d780acfde24a2bb16edd796b7c18c26d85ee8` | 2026-09-05 | tests/test_dashboard.py:1744-1800 checks only that some Store observation matches each ID, while dashboard.py:1323-1370 does not show ID propagation to every nested boundary. |
| 3 | absent | `AR-149.3-20260905-191655e4` | `761c7fa7eef6d05c6155626a5bfa2f2e16b7ca16f14e64e0e8938fcb602d4cec` | 2026-09-05 | tests/test_dashboard.py:1696-1741 and 1802-1910 show correlation between response headers and normal and error observations, but provide no evidence of correlation with Store instrumentation. |
| 4 | satisfied | `AR-149.4-20260905-2ed7b6b0` | `2594c0abeeab69b991ae507bdaecb9f715ce54a80d6d9f454c9a737da45baa8a` | 2026-09-05 | AR-149 evidence records 180 passing dashboard/disconnect tests and source identity with the installed runtime; AR-271 evidence records 1030 passing named spine tests; ADR-0105 explicitly makes exhaustive checks optional. |
