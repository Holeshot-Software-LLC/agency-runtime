---
title: "Gate expensive CI fanout behind same-revision quality contracts"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [ci, testing, cost, github-actions, release]
related:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/RELEASE_CHECKLIST.md
  - .github/workflows/ci.yml
  - tests/test_ci_sharding.py
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
id: ADR-0097
type: decision
deciders: [maintainers]
---

# ADR-0097: Gate expensive CI fanout behind same-revision quality contracts

## Context

The restored event policy avoids repeating the full compatibility matrix on
pull requests, but every other expensive CI root still starts before cheap
syntax, formatting, workflow-contract, dependency-consistency, and dashboard UI
checks finish. A malformed or mechanically invalid change can therefore consume
coverage, performance, Windows, artifact, and security runner minutes that
cannot change the outcome.

The quality job also checked out a pull request's head commit while downstream
jobs used GitHub's merge revision. Treating that as a same-revision prerequisite
would be false. History-derived documentation checks need the durable head and
complete history, while code and workflow checks need the same merge revision
as downstream execution.

## Decision

Run the first quality checkout at the event's default revision. On pull
requests, this is the merge revision used by downstream jobs. Perform package
installation, `pip check`, Ruff, formatting, whitespace, workflow/sharding
contracts, and dashboard UI coverage there. Re-check out the complete durable
pull-request head only after those checks and use it solely for documentation
metadata, policy availability, worklog, tracker, and history validation.

Make `quality-contracts` a prerequisite of the expensive coverage, performance,
compatibility, Windows portability, artifact, and security roots. Keep the
aggregate job under `if: always()` so a failed prerequisite and every propagated
skip are observed as failure rather than disappearing. Pull requests require
the compatibility job to be intentionally skipped; `main` and manual runs
require it to succeed after quality passes.

Remove the Ubuntu 24.04/Python 3.13 serial compatibility cell because the exact
non-performance file union already runs in four Python 3.13 coverage shards.
Retain serial ordering on Ubuntu/Python 3.10, 3.11, 3.12, and 3.14 plus Windows
3.10 and 3.14, retain uninstrumented Python 3.13 performance, and retain all
other production gates. Move whitespace and documentation validation to the
single quality job instead of repeating it in compatibility children.

## Consequences

- Fast deterministic failures stop expensive CI fanout and reduce runner cost.
- Code, workflow, dependency, and UI prerequisites cover the same PR merge
  revision as downstream jobs; history-derived ledgers still cover the durable
  head intentionally.
- Security and artifact jobs begin later. A malformed change receives no CI
  security result until it passes fast quality, but the aggregate cannot pass
  without their eventual success.
- Python 3.13 still executes the exact non-performance file union under four
  isolated coverage sessions, but that is not identical to one serial process:
  it does not reproduce cross-file ordering or one session-fixture lifetime on
  that exact tuple. The remaining six serial cells retain those behaviors across
  the supported-version and Windows endpoint matrix.
- CodeQL and dependency review remain independent workflows and are not delayed
  by this graph.
- The workflow defines a strict aggregate but does not itself enforce hosted
  branch policy. AR-159 owns that separately authorized repository setting.

## Alternatives

- **Start every gate immediately.** Rejected because known-fast failures still
  consume the largest runner budget.
- **Check the PR head in quality and the merge revision downstream.** Rejected
  because prerequisite success would describe a different source revision.
- **Remove all compatibility cells covered elsewhere.** Rejected because
  coverage shards and performance tests do not preserve the serial-session and
  supported-version contracts.
- **Delay CodeQL and dependency review too.** Rejected because they are separate
  security workflows with independent value and event contracts.
