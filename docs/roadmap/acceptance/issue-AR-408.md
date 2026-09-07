---
title: "AR-408 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, workforce, diagnostics]
related:
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-408
candidate_commit: d9dde3cd91c438c4d8a60e7b47f87c3df0a57cde
evidence_cutoff: 2026-09-07
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/732
---

# AR-408 acceptance verification record

## Builder evidence

Observations below bind the reviewed diagnostics repair and installed artifact.
They do not judge acceptance or claim a new successful model-host turn.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Only a valid negative critic verdict uses the veto helper | 2026-09-07 | agency_runtime/core/workforce/inference.py:4923-4955 |
| 1 | test | Exact five-call failure retains budget cause in a real Store | 2026-09-07 | tests/test_staffing_failure_receipts.py:93-123 |
| 1 | test | Missing provider, expired deadline, timeout, HTTP and invalid replies do not invent vetoes | 2026-09-07 | tests/test_staffing_failure_receipts.py:126-182 |
| 1 | test | Genuine negative verdict and valid approval remain unchanged | 2026-09-07 | tests/test_staffing_failure_receipts.py:185-212 |
| 1 | command-output | Red/green focused results and unchanged-budget scope | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#regression-first-then-repair |
| 2 | file | Effective allowance is set before the expired admission receipt | 2026-09-07 | agency_runtime/core/workforce/inference.py:1744-1795 |
| 2 | file | Workforce routing preserves effective timeout | 2026-09-07 | agency_runtime/core/workforce/routing_projection.py:248-277 |
| 2 | test | Real Store projection preserves allowance and excludes private fields | 2026-09-07 | tests/test_staffing_failure_receipts.py:215-238 |
| 2 | test | Shared deadline clips actual preflight to 65 seconds and persists 65000 ms | 2026-09-07 | tests/test_preflight_provider_deadline.py:20-63 |
| 2 | test | Expired-before-critic call does not persist positive allowance | 2026-09-07 | tests/test_staffing_failure_receipts.py:126-182 |
| 2 | test | Real Store failure helper and bounded projection | 2026-09-07 | tests/test_staffing_failure_receipts.py:64-90 |
| 2 | command-output | Focused production projection and deadline results | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#regression-first-then-repair |
| 3 | test | Full real orchestration with fixed responses and real Store persistence | 2026-09-07 | tests/test_staffing_failure_receipts.py:35-123 |
| 3 | command-output | Regression first: 8 failures then 23 passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#regression-first-then-repair |
| 3 | command-output | Relevant broader package: 325 passes, one skip, one deselection | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#broader-focused-verification |
| 3 | command-output | Independent 32-pass review and unchanged review/budget behavior | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#independent-review |
| 3 | command-output | Named production spine 1085 passes and UI 224 passes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#named-fast-verification |
| 3 | command-output | Exact wheel/sdist and installed CLI, MCP, dashboard and five generated host contracts | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md#exact-portable-artifact-and-installed-smoke |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|

