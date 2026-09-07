---
title: "AR-174 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, ci, documentation]
related:
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-174
candidate_commit: 452639dda089ea3304e04824beaf9b79e8c1febe
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
| 5 | test | Unconditional two-producer matrix and parity remain on documentation lane | 2026-09-07 | tests/test_release_packaging.py:966-980 |
| 5 | command-output | Historical five allocated runners and six skipped placeholders | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#job-times-and-calculation |
| 5 | command-output | Current aggregate tests pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 6 | command-output | Complete scope/workflow/sharding/session contract execution | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 6 | command-output | Bash syntax, release hygiene and pinned offline workflow security output | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#shell-and-security-transcript |
| 6 | command-output | Ruff and strict staged-record checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#record-checks |
| 7 | command-output | Exact eligible historical PR, successful hosted run, Git mode paths and helper blobs | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#hosted-run-and-pull-request |
| 7 | command-output | Raw allocated job times, successful topology, excluded placeholders and arithmetic | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#job-times-and-calculation |
| 8 | file | Existing bounded delivery authority makes exhaustive integration optional | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md#decision |
| 8 | command-output | Actual focused scope/workflow/sharding/session command and stdout | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#focused-workflow-transcript |
| 8 | command-output | Actual Bash/hygiene/offline workflow checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#shell-and-security-transcript |
| 8 | command-output | Actual fresh named production spine command and output tail | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#production-spine-transcript |
| 8 | command-output | Actual UI and current-floor coverage command/output | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#ui-and-current-coverage-transcript |
| 8 | command-output | Actual metadata/policy/worklog/strict docs/tracker/Ruff/diff outputs | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md#record-checks |

## Verification

First isolated review at 452639dd: criteria 2/3/4/6/8 satisfy; 1/5 need
their own full workflow call sites, and 7 lacks evidence of billing-account
repair despite a valid historical runner measurement. Preserve these results
before any citation or requirement correction. No builder-authored verdicts.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | absent | `AR-174.1-20260907-34cda92a` | `64b8ce2162579c1977ba36a8f9530fb950602f5563e93fccdf1512052dfd9b6b` | 2026-09-07 | scripts/classify_ci_change.py and tests/test_ci_change_scope.py show path filtering, but no workflow excerpt establishes trusted classifier execution or lane selection when the classifier itself changes. |
| 2 | satisfied | `AR-174.2-20260907-96999e5f` | `2aa8959ee96b9385562fc5a1d62aa136a68ada4b6c3949f6a9984372957cc623` | 2026-09-07 | The ci.yml excerpts show both helpers extracted from validated base-revision blobs into temporary files and executed with python -I; test_release_packaging.py pins both execution paths. |
| 3 | satisfied | `AR-174.3-20260907-959d3029` | `955104b32ab4503bbbe882fd87db79de9da095d81ef76d7f15fd748ac577b7ff` | 2026-09-07 | The cited tests in tests/test_release_packaging.py verify default merge checkout before code checks and exact-head checkout with HEAD validation for ledgers; the focused workflow transcript records their passing run. |
| 4 | satisfied | `AR-174.4-20260907-9817247a` | `3711dcc3957c1121ed6385ca83048eda5cd6f4b06c634768188d8283f9fcbb00` | 2026-09-07 | ci.yml shows unconditional Linux and Windows producers and dependent parity; test_release_packaging.py asserts docs are sdist inputs and producers remain enabled, with the focused transcript reporting passing tests. |
| 5 | absent | `AR-174.5-20260907-cd174969` | `54198d6017aae6747e5ff895bf706358b1c0b5c2ba7028b3cf8950bf4ff34e72` | 2026-09-07 | ci.yml:770-847 demonstrates strict result checks, but tests:966-980 omit the producer matrix and the historical job log cannot establish the exact five-runner topology at the candidate commit. |
| 6 | satisfied | `AR-174.6-20260907-768140ba` | `d8587c4874048a7b3b2bbce6d26f09ddcbe544edfde415d9a5abd0f5abbfa4a7` | 2026-09-07 | AR-174-docs-only-ci-20260907.md records 235 passing focused scope/workflow/sharding tests, successful Bash syntax and release-hygiene checks, offline zizmor with no findings, and passing Ruff lint and format checks. |
| 7 | absent | `AR-174.7-20260907-daaa68fe` | `b0c0b58c6b954427936bca9264bd2bf8d8098c08bd6138e914280cd8ff427535` | 2026-09-07 | The hosted-run and job-times excerpts document PR #380 at 6.10 raw runner-minutes, but do not establish that the billing/spending block was repaired before that run. |
| 8 | satisfied | `AR-174.8-20260907-c1f14719` | `3e868224950739086bfdc360dea63bf8974574e3414b46f91626e9d2fe8717dd` | 2026-09-07 | AR-174-docs-only-ci-20260907.md records successful commands and outputs for all required checks, including UI coverage above current thresholds, while ADR-0105 explicitly makes exhaustive diagnostics optional. |
