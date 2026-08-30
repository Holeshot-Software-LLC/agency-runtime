---
title: "Run exhaustive Python verification on demand"
status: superseded
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [ci, github-actions, cost, testing, coverage, release]
related:
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/decisions/0100-short-circuit-trusted-docs-only-pull-requests.md
  - .github/workflows/ci.yml
  - tests/test_ci_session_pair.py
  - tests/test_release_packaging.py
supersedes: []
superseded_by: docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
id: ADR-0101
type: decision
deciders: [maintainers]
---

# ADR-0101: Run exhaustive Python verification on demand

## Context

The exact warning-strict corpus takes about 32 minutes in one local process;
branch instrumentation has historically taken about 69 minutes. Four hosted
coverage shards reduce wall time but still consume substantial raw GitHub
Actions minutes on every code change. A non-instrumented four-shard substitute
would preserve test coverage but would still spend the same runner envelopes
on every pull request.

The owner explicitly prioritizes bounded hosted spend over automatic exhaustive
Python verification. Fast static, workflow, dashboard, portability, artifact,
and security contracts remain independently available.

## Decision

Run the four-shard Python 3.13 coverage corpus, combined 97-percent report, and
six-interpreter compatibility corpus only for an explicit
`workflow_dispatch`. Pull requests and ordinary pushes must skip those jobs.
The stable aggregate requires success for both manual integration surfaces and
requires an exact skipped result for automatic events; skipped coverage is
never represented as coverage success.

Keep the exhaustive commands in the release checklist and require a manual
full-verification dispatch before a release decision. Preserve the fast
automatic quality, dashboard, performance, Windows portability, artifact, and
security gates. The quality root includes a bounded Python production/security
spine so ordinary code changes still exercise routing, hiring, delegation,
state, protocol, installer, host-boundary, and operator-presence behavior.

## Consequences

- Code pull requests and pushes avoid three primary coverage runner allocations
  and all four instrumented shard sessions. Compatibility already skipped pull
  requests and now also skips ordinary pushes.
- Automatic checks no longer establish complete Python regression or aggregate
  coverage evidence. Their aggregate says those gates were skipped.
- A release requires an explicitly requested manual run; missing, skipped,
  failed, or cancelled integration evidence blocks that manual aggregate.
- The policy reduces expected spend structurally. Hosted minutes remain
  unmeasured while GitHub rejects runner allocation for billing reasons.

## Alternatives

- **Run four non-instrumented shards on every pull request.** Rejected by the
  owner because their hosted minutes remain material.
- **Keep coverage on pushes only.** Rejected because an ordinary push is not an
  explicit request to spend the exhaustive verification budget.
- **Remove exhaustive verification.** Rejected because production and release
  decisions still require current complete regression and coverage evidence.
