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
candidate_commit: f0f5c386e705dae51e9ac912139692caf53821f5
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
| 1 | satisfied | `AR-285.1-20260905-86857dfa` | `7a4182f118748267fb5fe56e387c62d036fd71365df567ee17f06d5bf5e5bb55` | 2026-09-05 | The evidence document records the nested exit-1 stopped receipt returning None in the parent classifier, which fails the focused regression’s assert live is False in tests/test_installer_registration.py:796-825. |
| 2 | absent | `AR-285.2-20260905-30ab30fd` | `13784b19e7e9dd9f449c4c948f783c615a43068cd4f97c077df78064ad66365b` | 2026-09-05 | installer_registration.py:123-178 demonstrates exit-1 triple classification, but neither it nor test_native_installer.py:1586-1602 demonstrates that executable and namespace trust remain enforced. |
| 3 | satisfied | `AR-285.3-20260905-14cff3c8` | `f123e5e8604e3328eb6086ea482f61bd98c8e594a3d10cf0974298eb5e456937` | 2026-09-05 | The replay table and installer_registration.py:123-178 show invalid, incomplete, and unsupported nonzero results cannot prove stopped, while live signals override stopped claims; tests at lines 760-793 verify unknown and live states block mutation. |
| 4 | satisfied | `AR-285.4-20260905-4818fd47` | `610019503a723f57144f8c3e3912e675ee8a806e648a7651d3f5fc43b298187d` | 2026-09-05 | The cited Focused checks section records the two-file installer and registration suite passing with 181 tests, exit 0, on Linux with Python 3.12. |
| 5 | absent | `AR-285.5-20260905-ee5009c0` | `fe31c8165be8390a14b1289b4ed217faf28a0bed448ac8551cd31898ccaac04c` | 2026-09-05 | AR-285 lines 34–81 describe rejected dry runs and a checked acceptance box; AR-119 records installs without gateway restarts but provides no successful changed-precondition dry-run evidence. |

## Verification availability

The first 2026-09-05 Claude verifier pass recorded no judgments. A subsequent
read-only transport inspection reported executable refused as untrusted because
its parent namespace permits substitution. No permissions were changed and no
model success is inferred from that pre-transport failure. The supported Codex
transport then judged the same per-criterion excerpts without repository
browsing tools. It returned three satisfied criteria and two absent criteria.
Both absent judgments are retained; the issue remains in_progress. Criterion 2
needs actual trusted-runner wiring evidence and criterion 5 needs a successful
changed-precondition dry-run receipt. No retry or host mutation was performed
to manufacture either missing proof.
