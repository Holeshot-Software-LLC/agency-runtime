---
title: "AR-174: Short-circuit documentation-only CI"
status: done
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [ci, github-actions, performance, cost, documentation, security]
related:
  - docs/decisions/0233-separate-hosted-run-timing-from-billing-administration.md
  - docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/decisions/0100-short-circuit-trusted-docs-only-pull-requests.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - .github/workflows/ci.yml
  - scripts/classify_ci_change.py
  - scripts/check_ci_whitespace.py
  - tests/test_ci_change_scope.py
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-174
priority: p1
tracker_url: null
depends_on: [AR-156]
blocks: []
---

# AR-174: Short-circuit documentation-only CI

## Problem

The primary pull-request workflow schedules thirteen hosted runner jobs even
when the complete change consists only of regular Markdown under `docs/`.
Coverage, wall-clock performance, Windows portability, and source security
analysis cannot produce different runtime evidence for such a delta, yet their
runner envelopes still consume time and budget.

A naive path filter is not sufficient. A pull request can alter its own scope
classifier, a clean checkout makes `git diff --check` inspect no committed
delta, code checks must remain on GitHub's merge revision, and every repository
Markdown document ships in the source distribution.

## Current state

One fail-closed quality job classifies the exact pull-request base-to-head
delta with a regular `100644` classifier materialized from the trusted base
commit and executed under isolated Python. Missing trusted logic bootstraps to
full CI. Only regular `docs/**/*.md` additions, modifications, or deletions can
select the reduced lane; code, workflow, classifier, root README, non-Markdown,
rename-from-code, executable, symlink, empty, malformed, push, and manual deltas
run the full graph or fail.

Eligible documentation pull requests retain quality/document validation, exact
committed-range whitespace validation, release hygiene, both Linux and Windows
artifact producers, byte-identical sdist and platform-wheel parity, and the
stable aggregate. Runtime coverage, performance, compatibility, Windows
portability, and source security fanout is skipped coherently. Code checks stay
on the default pull-request merge revision; only history-derived ledgers switch
to the exact durable head.

September 7 reconciliation confirms the implementation remains relevant and
unchanged. Fresh workflow/scope/sharding/session checks pass 235 cases with
five Windows-named deselections; all 18 explicit Bash workflow steps parse,
release hygiene passes and pinned offline zizmor has no findings beyond one
unchanged suppression. Fresh named spine passes 1085/three existing skips;
UI passes 204 with unchanged production coverage floors.

Historical hosted evidence was overlooked: August 31 PR #380 changed only
four regular docs Markdown files. Its successful run 33426445699 allocated
exactly five jobs totaling 366 raw seconds (6.10 runner-minutes), with runtime
fanout skipped. Trusted classifier/whitespace blobs match the current source.
This is one historical timing measurement, not current billing health, a
matched savings claim or new native-Windows execution. The complete read-only
API/Git receipts are linked below. First isolated verdicts are preserved at
5d20ec28: 2/3/4/6/8 satisfy; 1/5 need self-contained workflow/matrix citations,
and 7 lacks account-repair proof despite valid raw timing. ADR-0233 explicitly
separates timing from billing administration, retaining the original requirement
and avoiding any claim that the account was repaired. All eight criteria satisfy
at 5a003a059b52e4bc9e335e42a436768b95171446 in the second/final review.
AR-174 is done with no source change, copied verdicts or third review.

## Approach

Treat scope as a security decision. Read the classifier and whitespace helper
by blob identity from the trusted base revision, validate their regular-file
mode, execute with `python -I`, and bound Git evidence. Preserve the stable
aggregate check and require it to observe the exact success/skip topology for
the declared event. Keep artifact parity because Markdown changes source-
distribution bytes. Never use cross-run artifacts without a separate
provenance and cache-authority design.

## Dependencies

ADR-0037 requires pinned layered supply-chain gates. ADR-0097 requires expensive
fanout to remain same-revision and fail closed. AR-156 owns the larger measured
CI feedback program, while AR-159 owns separately authorized hosted branch
enforcement.

The existing pre-tracker exemption applies; no duplicate tracker is created.
ADR-0105 reconciles only the obsolete eighth universal gate before review.
ADR-0233 separately reconciles criterion 7 after preserving the first review.
All original wording is retained; criteria 1–6 are unchanged.

## Acceptance

- [x] Only a complete regular `docs/**/*.md` pull-request delta can select the
  reduced lane; every ambiguous or self-modifying case runs full or fails.
- [x] Classifier and whitespace policy execute from a trusted base-revision
  blob, not pull-request-controlled Python imports.
- [x] Code checks use the merge revision and history ledgers use the exact head.
- [x] Documentation-only changes retain both artifact producers and parity
  because docs are source-distribution inputs.
- [x] The aggregate accepts only the exact five-runner primary topology and
  rejects missing, failed, cancelled, or incoherent results.
- [x] Focused scope, workflow, sharding, shell, Ruff, release-hygiene, and
  offline workflow-security checks pass.
- [x] One exact eligible hosted pull-request run records raw runner minutes
  from allocated jobs' start/completion timestamps, with base/head, complete
  regular docs-only delta and successful five-runner topology; historical timing
  is dated and does not assert billing repair, current availability or savings.
- [x] Focused scope/workflow/sharding/session, Bash syntax, release hygiene,
  offline workflow security, named production spine, UI/current coverage,
  metadata, policy, worklog, strict docs/tracker, Ruff and diff checks pass;
  exhaustive integration remains optional under ADR-0105.

## Preserved original criteria

7. One eligible hosted pull request measures raw runner minutes after the
   GitHub Actions billing/spending block is repaired.
8. The final repository release gate passes at the implementation commit.

## Implementation evidence

Local structure proves five primary runner allocations instead of thirteen for
an eligible documentation pull request: quality/docs, Linux artifact, Windows
artifact, artifact parity, and aggregate. That avoids eight allocations, a
61.5 percent structural reduction. It is not a measured speed or billing claim.
After AR-177, an automatic code pull request uses ten primary allocations and
an explicit full-verification dispatch uses sixteen; the five-allocation
documentation lane is unchanged.
Eighteen scope/whitespace tests, fifty workflow/aggregate tests, and forty-three
combined scope/sharding/session tests pass. Current hosted jobs fail before
runner allocation because of the external Actions billing state, so hosted
duration remains deliberately unclaimed in that historical report. The
[September 7 receipt](acceptance/evidence/AR-174-docs-only-ci-20260907.md)
now records the overlooked August 31 five-runner measurement and current
bounded verification, without rewriting the old run's source or outcomes.
