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

All first verdicts remain at c456b6bd. This second record is frozen at
d30b8ae0f4f339d17c28b35f24d95e4474aa3bed with the historical comparison and
explicitly reconciled ninth criterion. No verdicts are carried across candidates;
all nine require new isolated checks.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
