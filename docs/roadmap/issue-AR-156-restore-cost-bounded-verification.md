---
title: "AR-156: Restore cost-bounded verification feedback"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [testing, ci, performance, cost, developer-experience]
related:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - .github/workflows/ci.yml
  - scripts/select_test_shard.py
  - tests/test_ci_sharding.py
  - tests/test_release_packaging.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-156
priority: p1
tracker_url: null
depends_on: [AR-117]
blocks: []
---

# AR-156: Restore cost-bounded verification feedback

## Problem

A later workflow change removed AR-117's event condition and now runs the
seven-cell full compatibility corpus on every pull-request edit. Local release
verification also has no supported parallel entrypoint, so developers routinely
wait 34-43 minutes for one serial warning-strict corpus and about 69 minutes for
coverage.

## Current state

Successful hosted evidence shows a PR with the deferred matrix used 23.33 raw
runner-minutes and completed in 4m50s, while a comparable current PR used
119.12 raw runner-minutes and completed in 29m19s. The unconditional matrix
alone accounted for 96.27 raw runner-minutes. The current workflow therefore
executes the non-performance corpus collectively under coverage and then seven
additional times per PR, despite AR-117 and the North Star explicitly deferring
the compatibility matrix to `main` or manual dispatch.

Recent hosted runs do not provide code evidence: GitHub rejects their jobs
before any step because account payments failed or the Actions spending limit
must be increased. This external state must not be reported as a test failure
or a green hosted gate.

## Approach

Restore the documented pull-request cadence and make the aggregate quality job
event-aware: pull requests must observe the compatibility job as intentionally
skipped, while `main` and manual runs must observe it as successful. Every other
required dependency remains success-only. Preserve the complete seven-cell
matrix unchanged on its governed events.

Add a cross-platform local runner that uses the same deterministic file
partitioner, creates an isolated private runtime and pytest base directory for
each shard, executes the exact warning-strict non-performance corpus in four
concurrent subprocesses, retains bounded logs, and returns failure unless every
shard succeeds. Keep the serial command as the canonical final release gate
until equivalence and repeated timing evidence justify changing that policy.

## Dependencies

AR-117 and the North Star own the existing hosted cadence. ADR-0030 requires
quantitative claims to use recorded controls rather than inferred speedups.

## Acceptance

- Pull requests require the compatibility job to be intentionally skipped;
  `main` and manual runs require it to succeed.
- No aggregate path accepts cancelled, failed, missing, or unexpectedly skipped
  production gates.
- The seven compatibility cells and all PR coverage, performance, portability,
  artifact, security, documentation, and UI gates remain intact.
- Workflow contract tests pin the exact event/result policy and reject a future
  unconditional compatibility regression.
- The local runner proves serial/sharded test collection equivalence, uses one
  private runtime and base directory per shard, aggregates failures, and cleans
  up safely.
- Three comparable warm local runs demonstrate at least 30 percent median
  wall-clock improvement before the parallel runner is recommended as the
  default change loop.
- After GitHub billing or spending state is repaired, one PR run and one
  `main` or manual run provide hosted URLs and exact job evidence.
