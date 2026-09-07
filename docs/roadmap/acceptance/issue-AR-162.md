---
title: "AR-162 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, ci, security]
related:
  - docs/roadmap/acceptance/evidence/AR-162-record-reconciliation-20260907.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-162
candidate_commit: d30b8ae0f4f339d17c28b35f24d95e4474aa3bed
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-162 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | All events reach one capability job with exactly one bounded curl request before analysis expansion | 2026-09-07 | .github/workflows/codeql.yml:1-50 |
| 1 | test | Workflow contract counts one probe, checks no preflight checkout and pins request/time/output boundaries | 2026-09-07 | tests/test_release_packaging.py:1478-1516 |
| 1 | command-output | Final governed workflow package passes 210 cases without failure | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#fresh-verification |
| 2 | file | Bounded strict JSON classification rejects unknown status/visibility and limits unavailable classification to exact private/internal messages | 2026-09-07 | .github/workflows/codeql.yml:50-130 |
| 2 | test | Harness executes the actual embedded classifier and records emitted output | 2026-09-07 | tests/test_release_packaging.py:1519-1553 |
| 2 | test | Missing/malformed/unbounded/ambiguous/public entitlement cases require failure and no availability output | 2026-09-07 | tests/test_release_packaging.py:1596-1698 |
| 2 | command-output | Actual shell missing-body reproduction changes from false availability to failure with empty stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#baseline-and-repair |
| 3 | file | Exact available-only two-language matrix retains immutable pins, queries, categories and SARIF upload | 2026-09-07 | .github/workflows/codeql.yml:179-208 |
| 3 | test | Available analyzer contract pins all language, action, query, category, upload and permission settings | 2026-09-07 | tests/test_release_packaging.py:1701-1734 |
| 3 | command-output | Current analyzer configuration tests pass within the final workflow package; no hosted execution inferred | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#fresh-verification |
| 4 | file | Unavailable recorder writes both language-specific false-analysis records and one retained artifact | 2026-09-07 | .github/workflows/codeql.yml:131-178 |
| 4 | file | Only available=true admits CodeQL actions | 2026-09-07 | .github/workflows/codeql.yml:179-208 |
| 4 | test | Executed recorder validates both language documents, false-analysis fields, upload path and retention | 2026-09-07 | tests/test_release_packaging.py:1737-1795 |
| 5 | file | Preflight declares only contents and code-scanning read permissions | 2026-09-07 | .github/workflows/codeql.yml:20-32 |
| 5 | file | Only analyzer has security-events write; stable aggregate declares contents read | 2026-09-07 | .github/workflows/codeql.yml:179-218 |
| 5 | test | Workflow tests pin root and aggregate least privilege plus exact job names | 2026-09-07 | tests/test_release_packaging.py:1456-1475 |
| 6 | file | Always-running stable result accepts only coherent preflight/analysis outcomes and rejects every other combination | 2026-09-07 | .github/workflows/codeql.yml:210-259 |
| 6 | test | Actual aggregate code executes two coherent cases and rejects missing, failed, cancelled, skipped and inconsistent prerequisites | 2026-09-07 | tests/test_release_packaging.py:1798-1846 |
| 6 | command-output | Aggregate cases pass in the final warning-strict workflow run | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#fresh-verification |
| 7 | file | Push, PR, weekly cron, manual dispatch and concurrency are unchanged | 2026-09-07 | .github/workflows/codeql.yml:1-17 |
| 7 | command-output | Exact pre-fan-out and repaired Git blobs have identical event/concurrency projections with full commit and blob hashes retained | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-record-reconciliation-20260907.md#historical-event-and-concurrency-comparison |
| 7 | test | Exact event and concurrency dictionary assertions preserve the original triggers | 2026-09-07 | tests/test_release_packaging.py:1456-1475 |
| 8 | file | ADR-0226 prohibits unsupported savings assertions and retains future matched measurement proof | 2026-09-07 | docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md#decision |
| 8 | command-output | Current public/non-fork identity and successful calling-identity endpoint read are separated from unproven workflow-token and hosted checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#current-capability-and-hosted-limits |
| 8 | file | No current speed or billing claim; original telemetry is historical and future claims retain the matched-measurement condition | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#measurement-boundary |
| 9 | file | AR-347 records the owner-approved self-shrinking pre-tracker exemption and both strict gates | 2026-09-07 | docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md:113-137 |
| 9 | file | The governed exemption explains its rules and includes AR-162 | 2026-09-07 | docs/roadmap/pre-tracker-history.txt:1-42 |
| 9 | file | ADR-0226 explicitly reconciles criterion 9 to the existing rule rather than claiming old remote parity | 2026-09-07 | docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md#decision |
| 9 | command-output | Current unmapped identity and strict docs/tracker results are retained without creating a duplicate | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-record-reconciliation-20260907.md#verification-and-unchanged-implementation |
| 9 | file | Canonical internal identity and null tracker remain | 2026-09-07 | docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md:1-40 |

## Verification

All nine isolated checks satisfy at d30b8ae0f4f339d17c28b35f24d95e4474aa3bed
in the second and final review. All first verdicts remain at c456b6bd; none was
carried across candidates. Historical comparison and the explicitly reconciled
ninth criterion are included in this candidate. Workflow and test bytes remain
unchanged from fcdcd6eb.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-162.1-20260907-c5a3818b` | `f96a99a5b567ce6552fe8b9c13f81b8d6975c1d9a14edd5b1bf95fb3ba5444b1` | 2026-09-07 | The unconditional capability job in .github/workflows/codeql.yml:1-50 serves all four event triggers with one curl request, and tests/test_release_packaging.py:1478-1516 asserts exactly one probe across all jobs. |
| 2 | satisfied | `AR-162.2-20260907-0a356c75` | `891386d59c665f98324e5a56eece241a1a7cd240e0cf903dc42505d79fed631e` | 2026-09-07 | The classifier in .github/workflows/codeql.yml:50-130 rejects malformed, unauthorized, unexpected and ambiguous responses before publishing output; only recognized private/internal HTTP 403 entitlement messages select unavailable, with rejection cases covered in tests:1596-1698. |
| 3 | satisfied | `AR-162.3-20260907-3d57da8c` | `0cf518e9deaaef7cdf1eb3892b5d9dc70b8330d561972662c48c9d2d0ae53876` | 2026-09-07 | The workflow excerpt at .github/workflows/codeql.yml:179-208 gates the exact Python and JavaScript/TypeScript matrix on availability and specifies pinned actions, security-extended queries, language categories, and upload: always; the cited test asserts these settings. |
| 4 | satisfied | `AR-162.4-20260907-3f7c6036` | `c1cee4c1b4213992172e23748ce678065261fcecda2aac70518036aa71d1518d` | 2026-09-07 | codeql.yml:131-208 gates CodeQL actions on available=true and uploads both language-specific JSON records with analysis_performed=false and seven-day retention; test_release_packaging.py:1737-1795 checks the recorder and upload path. |
| 5 | satisfied | `AR-162.5-20260907-ed6a4627` | `89655083f7706af2e7e387df62fb22b146dc39df4415f7f1f52ee58c0e48c93b` | 2026-09-07 | The codeql.yml excerpts grant security-events write only to analyze, security-events read to capability, and contents read to codeql; the test excerpt pins the three-job set and read-only root permissions. |
| 6 | satisfied | `AR-162.6-20260907-b4035c14` | `a7eb77009feb41ed3392e92df3f3dbc040bf390bfef5a52674130dd1cfefbcd0` | 2026-09-07 | The always-running CodeQL result in .github/workflows/codeql.yml:210-259 accepts only two coherent prerequisite combinations and rejects all others; tests/test_release_packaging.py:1798-1846 covers missing, failed, cancelled, invalid and inconsistent outcomes. |
| 7 | satisfied | `AR-162.7-20260907-6b63c29b` | `31fae0df6473fcdf0fe98782651de5ab783e211b7a23bf16a5801e48136e0ff9` | 2026-09-07 | codeql.yml:1-17 matches the identical historical event and concurrency projections recorded in AR-162-record-reconciliation-20260907.md, with exact assertions in test_release_packaging.py:1456-1475. |
| 8 | satisfied | `AR-162.8-20260907-c2bbfb18` | `48f0e076e406b6ec2fdb0e3882cdd9c5e0e39575c269dce7c26e927a3c7f1706` | 2026-09-07 | The AR-162 capability receipt distinguishes calling-identity access from unproven workflow-token authority and hosted checks, while its measurement boundary and ADR-0226 withhold savings claims pending matched hosted topology and raw-duration evidence. |
| 9 | satisfied | `AR-162.9-20260907-ba6c804e` | `65eeef69ef9b062fb90e607c4d256614ae8d91723088dfeebfe38e894ea34536` | 2026-09-07 | pre-tracker-history.txt lists AR-162, its local record has tracker_url null, the reconciliation artifact records both strict checks passing, and ADR-0226 requires exact URL/state parity upon mapping. |
