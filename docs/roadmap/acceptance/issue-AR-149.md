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
candidate_commit: pending
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
