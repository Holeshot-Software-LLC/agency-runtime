---
title: "AR-174 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, ci, documentation]
related:
  - docs/decisions/0233-separate-hosted-run-timing-from-billing-administration.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-174
candidate_commit: pending
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-174 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Complete bounded raw Git delta and regular docs-only mode/path admission | 2026-09-07 | scripts/classify_ci_change.py:56-151 |
| 1 | test | Docs additions/modifications, root/code/classifier changes, rename and empty events | 2026-09-07 | tests/test_ci_change_scope.py:81-153 |
| 1 | test | Malformed identity, merge-checkout, executable and symlink fail-closed cases | 2026-09-07 | tests/test_ci_change_scope.py:156-233 |
| 1 | command-output | All focused scope and workflow tests pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 1 | file | Actual workflow derives outputs by trusted-base helper and gates the reduced lane | 2026-09-07 | .github/workflows/ci.yml:24-110 |
| 1 | file | CLI emits only the classifier result as governed boolean and reason | 2026-09-07 | scripts/classify_ci_change.py:154-186 |
| 2 | file | Trusted base classifier mode/blob checks, fallback and isolated Python | 2026-09-07 | .github/workflows/ci.yml:42-86 |
| 2 | file | Whitespace helper requires trusted base regular blob and isolated Python | 2026-09-07 | .github/workflows/ci.yml:118-166 |
| 2 | test | Workflow contract pins both trusted blob execution paths | 2026-09-07 | tests/test_release_packaging.py:784-839 |
| 2 | command-output | Focused contracts executed | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 3 | test | Code checks precede exact-head ledger checkout and downstream default revision | 2026-09-07 | tests/test_release_packaging.py:924-963 |
| 3 | test | History checkout requires complete exact durable head | 2026-09-07 | tests/test_release_packaging.py:1120-1160 |
| 3 | command-output | All current workflow contracts pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 4 | test | Documentation ships in sdist and both producers plus parity remain unconditional | 2026-09-07 | tests/test_release_packaging.py:966-980 |
| 4 | file | Artifact producers preserve Linux/Windows profiles at the same event revision | 2026-09-07 | .github/workflows/ci.yml:541-561 |
| 4 | file | Parity depends on producer matrix and exact event commit | 2026-09-07 | .github/workflows/ci.yml:675-711 |
| 4 | command-output | Current artifact topology contracts pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 5 | file | Stable aggregate requires exact coherent results for current event and docs scope | 2026-09-07 | .github/workflows/ci.yml:770-847 |
| 5 | test | Failed missing cancelled or incoherent gate results fail closed | 2026-09-07 | tests/test_release_packaging.py:1010-1105 |
| 5 | file | Exactly two unconditional artifact producer matrix allocations | 2026-09-07 | .github/workflows/ci.yml:541-561 |
| 5 | file | One quality root emits the scope result | 2026-09-07 | .github/workflows/ci.yml:24-41 |
| 5 | file | One parity job depends on the complete artifact producer matrix | 2026-09-07 | .github/workflows/ci.yml:678-690 |
| 5 | test | All other roots are scope-gated and exhaustive roots also require manual dispatch | 2026-09-07 | tests/test_release_packaging.py:710-745 |
| 5 | command-output | Current aggregate tests pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 6 | command-output | Complete scope/workflow/sharding/session contract execution | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 6 | command-output | Bash syntax, release hygiene and pinned offline workflow security output | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#shell-and-security-transcript |
| 6 | command-output | Ruff and strict staged-record checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#record-checks |
| 7 | command-output | Exact eligible historical PR, successful hosted run, Git mode paths and helper blobs | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#hosted-run-and-pull-request |
| 7 | command-output | Raw allocated job times, successful topology, excluded placeholders and arithmetic | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#job-times-and-calculation |
| 7 | file | Explicit reconciliation separates measured execution from billing account administration | 2026-09-07 | docs/decisions/0233-separate-hosted-run-timing-from-billing-administration.md#decision |
| 8 | file | Existing bounded delivery authority makes exhaustive integration optional | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |
| 8 | command-output | Actual focused scope/workflow/sharding/session command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 8 | command-output | Actual Bash/hygiene/offline workflow checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#shell-and-security-transcript |
| 8 | command-output | Actual fresh named production spine command and output tail | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#production-spine-transcript |
| 8 | command-output | Actual UI and current-floor coverage command/output | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#ui-and-current-coverage-transcript |
| 8 | command-output | Actual metadata/policy/worklog/strict docs/tracker/Ruff/diff outputs | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#record-checks |

## Verification

First verdicts are preserved at 5d20ec28 before this new final candidate.
Pending eight fresh isolated checks; no earlier verdict is copied.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
