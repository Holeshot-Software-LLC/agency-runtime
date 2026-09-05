---
title: "AR-285 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, backlog]
related:
  - docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/acceptance/evidence/AR-285-backlog-verification-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-285
candidate_commit: pending
evidence_cutoff: 2026-09-05
tracker_url: null
---

# AR-285 acceptance verification record

Builder rows separate fresh source/test evidence from historical install
evidence. The isolated verifier supplies every judgment; the builder supplies
none. This does not assert current-version OpenClaw live activation.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `Parent versus current offline replay: identical nested exit-1 receipt returns unknown before repair and proven stopped now` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-285-backlog-verification-20260905.md#regression-and-negative-case-replay` |
| 1 | test | `Exact native command and stopped/inactive/dead receipt regression` | 2026-09-05 | `tests/test_installer_registration.py:796-825` |
| 2 | file | `Production classifier accepts only the bounded exit-1 triple; native command still goes through the existing trusted runner` | 2026-09-05 | `agency_runtime/core/installer_registration.py:123-178` |
| 2 | test | `Installer refuses a live gateway before any target or plugin mutation` | 2026-09-05 | `tests/test_native_installer.py:1586-1602` |
| 3 | file | `Complete current negative-case replay includes malformed, truncated, contradictory, partial, live and wrong-exit receipts` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-285-backlog-verification-20260905.md#regression-and-negative-case-replay` |
| 3 | file | `Production unknown/live exits remain fail-closed` | 2026-09-05 | `agency_runtime/core/installer_registration.py:123-178` |
| 3 | test | `Registration rejects unknown and live before any mutating command` | 2026-09-05 | `tests/test_installer_registration.py:760-793` |
| 4 | file | `Current two-file focused installer/registration execution record, separate from wider release-fixture failures` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-285-backlog-verification-20260905.md#focused-checks` |
| 5 | file | `Original changed-precondition dry-run and install account, after executable and parent trust refusals` | 2026-09-05 | `docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md:34-81` |
| 5 | file | `Historical clean installed checkout, exact install identity and digests; installer did not restart gateway` | 2026-09-05 | `docs/roadmap/AR-119-openclaw-hermes-verification-packet.md:204-232` |
| 5 | file | `Additional retained stopped-host installation bundle` | 2026-09-05 | `docs/roadmap/AR-119-openclaw-hermes-verification-packet.md:1050-1066` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
