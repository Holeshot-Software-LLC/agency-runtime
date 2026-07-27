---
title: "AR-162: Collapse unavailable CodeQL fanout"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [testing, security, ci, performance, cost, github-actions]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - .github/workflows/codeql.yml
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-162
priority: p1
tracker_url: null
depends_on: []
blocks: [AR-159]
---

# AR-162: Collapse unavailable CodeQL fanout

## Problem

The CodeQL workflow expands its language matrix before discovering whether the
repository can use native code scanning. When Code Security is unavailable,
two hosted runners independently check out the same revision, issue the same
entitlement request, record equivalent unavailable evidence, and exit without
performing analysis.

## Current state

Two observed successful unavailable-capability runs consumed 0.34 raw
runner-minutes on a pull request and 0.24 raw runner-minutes on a push. Each run
used two language jobs and performed no CodeQL analysis. These durations are
historical execution telemetry, not evidence that the replacement is faster
and not a claim about GitHub's rounded billing units.

## Approach

Run one least-privilege, fail-closed capability preflight before matrix
expansion. When native CodeQL is available, preserve the exact Python and
JavaScript/TypeScript matrix, pinned actions, query suite, categories, and SARIF
upload behavior. When it is unavailable, retain one artifact containing
language-specific evidence that explicitly says analysis was not performed.

Publish one stable aggregate job after the preflight and matrix. It accepts only
the two coherent states: successful preflight plus successful analysis matrix,
or successful unavailable classification plus an intentionally skipped matrix.
Missing, failed, cancelled, malformed, and inconsistent states fail closed.

## Dependencies

ADR-0037 governs layered supply-chain analysis. ADR-0097 governs cost-bounded
CI topology without weakening exact verification. AR-159 will use the stable
aggregate only after current hosted check names and repository protection are
explicitly authorized and verified.

## Acceptance

- Every workflow event performs exactly one native CodeQL capability request.
- Public, ambiguous, malformed, unauthorized, and unexpected probe responses
  fail closed; only the recognized private/internal missing-entitlement response
  selects the unavailable path.
- Available repositories run the exact Python and JavaScript/TypeScript CodeQL
  analyses with the existing pinned actions, `security-extended` queries,
  categories, and SARIF upload behavior.
- Unavailable repositories initialize no CodeQL action and retain both
  language-specific evidence records with `analysis_performed: false`.
- Only the analysis job receives `security-events: write`; the preflight has
  read-only code-scanning access and the aggregate has contents read access.
- One stable aggregate rejects missing, failed, cancelled, malformed,
  unexpectedly skipped, or otherwise inconsistent prerequisite results.
- Push, pull-request, weekly schedule, manual-dispatch, and concurrency behavior
  remain unchanged.
- A matched hosted unavailable-path run records the new job topology and raw
  runner duration before any speed or billing-savings claim is accepted.
- The tracker issue and local roadmap record have exact URL/state parity after
  tracker creation is authorized.

## Implementation evidence

The local workflow now uses one capability job, the unchanged two-language
analysis matrix when available, and one stable `CodeQL result` aggregate. The
unavailable recorder emits both language documents in one artifact and cannot
claim analysis. Focused contract tests execute both coherent aggregate paths,
reject adversarial result combinations, execute and inspect unavailable
evidence, pin event and permission boundaries, and preserve exact analyzer
configuration.

The old unavailable path used two 0.12-0.17-minute language runners. Replacing
the duplicated checkout, probe, and upload work with one preflight plus a small
aggregate is expected to reduce raw execution time, but the amount is unmeasured
and GitHub may round each hosted job independently. This change therefore makes
no current billable-minute savings claim. Hosted validation and tracker
creation remain pending authorization and repair of the external Actions
billing/spending block.
