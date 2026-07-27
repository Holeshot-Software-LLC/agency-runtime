---
title: "Short-circuit trusted documentation-only pull requests"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [ci, github-actions, cost, documentation, security, release]
related:
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - .github/workflows/ci.yml
  - scripts/classify_ci_change.py
  - scripts/check_ci_whitespace.py
  - tests/test_ci_change_scope.py
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0100
type: decision
deciders: [maintainers]
---

# ADR-0100: Short-circuit trusted documentation-only pull requests

## Context

Primary CI now uses thirteen pull-request jobs after the broader pairing work.
Scheduling all runtime gates for a Markdown-only documentation delta consumes
hosted budget without changing runtime evidence. Scope classification itself is
an authority boundary: running a classifier from the pull-request checkout
would let a code change suppress the tests meant to inspect it.

Repository documentation is also part of the source distribution. A
documentation change can affect sdist content and cross-platform parity even
when it cannot affect Python or browser behavior.

## Decision

Permit a reduced primary-CI lane only for pull requests whose complete
base-to-head raw Git delta contains one or more regular, non-executable
`docs/**/*.md` entries and nothing else. Materialize the classifier and
committed-whitespace helper from regular `100644` blobs at the trusted base
revision, run them with isolated Python, bound their evidence, and default to
full CI whenever the trusted helper is absent or any shape is ambiguous.

Keep code/static/UI/release-hygiene checks on GitHub's default pull-request
merge revision. Check out the exact head only for full-history documentation
ledgers. On the reduced lane, retain documentation validation, release hygiene,
committed-range whitespace validation, both cross-OS artifact producers,
artifact parity, and the stable aggregate. Skip runtime coverage, performance,
compatibility, Windows portability, and source-security fanout. Push and manual
runs always use full verification.

Treat job-count change as structure, not measured savings. Do not trust a
cross-run wheel or sdist until a separate decision defines immutable producer
identity, cache provenance, expiry, and invalidation.

## Consequences

- Eligible documentation pull requests use five primary runners instead of
  thirteen while still verifying the release bytes they change.
- Self-modifying classifiers, workflows, executable/symlink documents, root
  files, and malformed or empty deltas cannot choose the reduced lane.
- A documentation-only pull request does not re-run runtime behavior gates;
  the next push to `main` still runs the complete graph.
- CodeQL and dependency review are separate workflows and remain outside this
  primary-workflow decision.
- Hosted timing and billing savings remain unknown until GitHub allocates
  runners for a matched eligible pull request.

## Alternatives

- **Use workflow `paths-ignore`.** Rejected because stable required checks can
  disappear and cross-OS source-distribution validation would be skipped.
- **Execute the classifier from the pull-request checkout.** Rejected because a
  code change could classify itself as documentation-only.
- **Skip artifact jobs.** Rejected because all repository Markdown is included
  in the source distribution.
- **Reuse artifacts from another run.** Deferred until immutable cross-run
  cache authority and provenance have a governed design and measured proof.
