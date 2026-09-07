---
title: "AR-162 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, ci, security]
related:
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-162
candidate_commit: fcdcd6ebee6b522281d23a49d2bdc5f95c6649f9
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
| 7 | test | Exact event and concurrency dictionary assertions preserve the original triggers | 2026-09-07 | tests/test_release_packaging.py:1456-1475 |
| 8 | file | ADR-0226 changes only the measurement criterion to prohibit unsupported savings assertions while retaining future matched proof | 2026-09-07 | docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md#decision |
| 8 | command-output | Current public/non-fork identity and successful calling-identity endpoint read are separated from unproven workflow-token and hosted checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#current-capability-and-hosted-limits |
| 8 | file | No current speed or billing claim; original telemetry is historical and future claims retain the matched-measurement condition | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#measurement-boundary |
| 9 | file | Existing pre-tracker exemption explains its rule and explicitly lists AR-162 | 2026-09-07 | docs/roadmap/pre-tracker-history.txt:1-42 |
| 9 | file | Canonical issue retains null tracker identity and its existing internal ID | 2026-09-07 | docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md:1-40 |
| 9 | file | No tracker is created or duplicated; the applicable existing exemption and pre-completion state are explicit | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md#tracker-history |

## Verification

The first isolated review at fcdcd6eb satisfies criteria 1–6 and 8. Criterion 7
lacks a cited prior configuration; criterion 9 lacks remote parity under its old
wording despite the present pre-tracker exemption. Preserve these verdicts before
repairing evidence or explicitly reconciling the tracker requirement. No closure.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-162.1-20260907-e16aa023` | `503ad3618eb29813dbba7df1b3c2672bf08d9ecb4d3444f7e60b7038abd834da` | 2026-09-07 | The workflow excerpt routes all four event types to one unconditional capability job with one curl request, and tests/test_release_packaging.py asserts a single probe across all jobs. |
| 2 | satisfied | `AR-162.2-20260907-64c563f5` | `1ec7a8df881491eb64d3aa326d1b2394a1e61acd8ff241b258c42d1ef223e280` | 2026-09-07 | The classifier in .github/workflows/codeql.yml:50-130 rejects invalid bodies, statuses and ambiguous or public 403s before output; only recognized private/internal entitlement messages select unavailable, with rejection tests at tests/test_release_packaging.py:1596-1698. |
| 3 | satisfied | `AR-162.3-20260907-7ffc8a85` | `5ecc0aa7666c306cba7f73fe8739c2b96305296e40b1ec0b031bf72c0bc78408` | 2026-09-07 | The workflow excerpt at .github/workflows/codeql.yml:179-208 and contract test at tests/test_release_packaging.py:1701-1734 demonstrate the available-only Python and JavaScript/TypeScript matrix, pinned actions, security-extended queries, categories, and SARIF upload. |
| 4 | satisfied | `AR-162.4-20260907-ddb0e744` | `1dc38d4c9f18fcac40e5ae31fa19850214858f1c90ea3b3041358a8b5f6a72eb` | 2026-09-07 | The codeql.yml excerpts gate CodeQL initialization on available=true and, when false, write python and javascript-typescript records with analysis_performed=false and upload both with seven-day retention. |
| 5 | satisfied | `AR-162.5-20260907-f75d8464` | `4a49e69b7833fa6f567e97678c68d6c3fb986d5956ce2f5e8b38b942eb8123b8` | 2026-09-07 | The codeql.yml excerpts grant security-events write only to analyze, security-events read to capability, and contents read to codeql; the cited test asserts these are the only jobs. |
| 6 | satisfied | `AR-162.6-20260907-55385162` | `dcfe8df209fcee444333d21bba29fdd5e6d7e6621aaaa82d9a659dc1033d8efb` | 2026-09-07 | The always-running CodeQL result in .github/workflows/codeql.yml:210-259 accepts only two coherent prerequisite combinations and rejects all others; tests/test_release_packaging.py:1798-1846 covers missing, failed, cancelled, malformed and inconsistent outcomes. |
| 7 | absent | `AR-162.7-20260907-8840edb0` | `3cc6162d582aa9a6270daa6f701a46bf4a2323532d118df646ee5fdf83fd2b58` | 2026-09-07 | The codeql.yml and test_release_packaging.py excerpts establish current triggers and concurrency settings, but provide no prior configuration to verify that behavior remains unchanged. |
| 8 | satisfied | `AR-162.8-20260907-c49cd62a` | `629b680ec2feabcf8a1abb62a60f9abc66b8ce4c23ed48458ca7b88fce117365` | 2026-09-07 | AR-162-codeql-capability-20260907.md distinguishes calling-identity availability from unproven workflow-token authority and hosted checks, makes no current savings claim, and retains ADR-0226's matched hosted topology and raw-duration measurement requirement. |
| 9 | absent | `AR-162.9-20260907-2ce4da74` | `c2728e60322f2d2251efe3843ae18f6c6f5aa9413739f93609ce552a9b2a9465` | 2026-09-07 | The roadmap excerpt has tracker_url null, and the tracker-history receipt cites a legacy exemption; neither demonstrates tracker creation authorization or exact remote URL/state parity. |
