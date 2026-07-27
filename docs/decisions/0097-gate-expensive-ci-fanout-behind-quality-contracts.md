---
title: "Gate expensive CI fanout behind same-revision quality contracts"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [ci, testing, cost, github-actions, release]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/decisions/0100-short-circuit-trusted-docs-only-pull-requests.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/RELEASE_CHECKLIST.md
  - .github/workflows/ci.yml
  - .github/workflows/codeql.yml
  - .github/workflows/dependency-review.yml
  - scripts/run_ci_session_pair.py
  - tests/test_ci_sharding.py
  - tests/test_ci_session_pair.py
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

Pair hosted jobs, not test processes. Schedule the four unchanged Python 3.13
coverage shards as two concurrent Ubuntu job pairs and the six compatibility
sessions as three concurrent OS-matched job pairs: Linux 3.10+3.11, Linux
3.12+3.14, and Windows 3.10+3.14. Each member keeps its exact setup-python
interpreter and runs pytest in a separate attested runtime and owned process
tree with disjoint HOME, TEMP, pytest base, and COVERAGE_FILE paths. Preserve
matrix `fail-fast: false` within each pair: an ordinary test failure does not
cancel its peer. Controller failure, interruption, timeout, missing coverage,
or truncated bounded evidence fails closed and quiesces both process trees.
Compatibility retains one `pip check` per interpreter under a short independent
bound. GitHub command-file and credential capabilities do not cross into
interpreter probes, runtime preparation, pytest, or `pip check`; nonsecret
revision, workspace, runner, and CI identity remain available.

Keep the outer hosted timeout strictly above the sum of sequential preparation
and the longest member's phase bounds, with cleanup and pre-controller setup
margin. Under the current controller constants, coverage requires a 35-minute
job ceiling and compatibility requires 70 minutes. These values are failure
ceilings, not expected duration or cost claims.

Independently, perform the CodeQL entitlement probe once before its language
matrix expands. Preserve both exact language analyses when available. When
unavailable, retain explicit per-language non-analysis evidence, and converge
both paths on one stable aggregate that rejects missing, failed, cancelled,
malformed, or inconsistent prerequisite results.

Keep dependency review in one stable job. Bound its authenticated repository
identity and comparison requests, accept fallback only for the exact scoped
private/internal non-fork HTTP 403 capability tuple, label installed-runtime
auditing as non-equivalent compensating evidence, and converge native and
recognized-fallback paths on one fail-closed aggregate without adding a runner.

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
- Coverage and compatibility retain four and six independently isolated Python
  sessions respectively while using five hosted jobs instead of ten. This
  removes duplicated job envelopes but introduces same-runner CPU, memory, and
  I/O contention. Any runner-minute reduction remains a projection until
  matched green hosted evidence exists; job-count reduction alone is not a
  measured speed or cost claim.
- A workflow timeout below the controller envelope can preempt contained
  classification and cleanup. The paired topology is not release-ready unless
  the hosted ceilings implement the 35-/70-minute decision or the inner bounds
  are reduced with equivalent evidence.
- CodeQL and dependency review remain independent workflows and are not delayed
  by the primary CI graph. CodeQL internally gates its exact language matrix on
  one fail-closed entitlement preflight and exposes one stable aggregate result.
- Dependency review retains one hosted job. Its bounded probe prevents an
  ambiguous API response or network stall from becoming a green fallback path,
  but duration and billing effects remain unmeasured until matched hosted runs.
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
- **Merge each pair into one pytest process.** Rejected because cross-version
  execution is impossible and one process would merge HOME, fixture lifetime,
  ordering, coverage, and failure evidence that remain independent gates.
- **Cancel the peer on the first test failure.** Rejected because the prior
  matrix explicitly used `fail-fast: false`; both applicable session results
  remain useful even when the aggregate must fail.
- **Delay CodeQL and dependency review behind primary CI.** Rejected because
  they are separate security workflows with independent value and event
  contracts. CodeQL's own entitlement preflight is not such a delay; it avoids
  knowingly useless fanout while preserving analysis whenever it is available.
