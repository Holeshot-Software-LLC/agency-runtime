---
title: "Worklog detail: Bind measured Windows sharding"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, windows, performance, evidence, security]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 11241e61721abf4e7438d529e3c70323d9334b53
short: 11241e6
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Bind measured Windows sharding

## Purpose

Turn Windows per-file timing from diagnostic output into source-bound evidence
that can safely drive a faster local change loop, while removing unrelated test
setup that was consuming developer feedback time.

## Approach

The v2 producer records the complete planned partition and a measurement
context covering the clean Git commit, product and test content, timing harness,
runtime family, worker count, and corpus semantics. The profile generator
strictly validates files, phases, shard aggregates, identities, and bounded
non-link inputs, then independently reproduces the explicit source-byte control
assignment before accepting three distinct samples. The runner revalidates
source both before execution and before timing publication.

Profiles use duration-weighted longest-processing-time assignment only when the
test, harness, and runtime contracts match. Product edits remain visibly
`compatible` for the ordinary change loop, while strict benchmark mode requires
the exact measured product digest. Missing, invalid, stale, unsupported, and
explicit source-byte states remain whole-corpus fallbacks rather than mixing
trusted and untrusted weights.

Four test fixtures now construct only the state their assertions consume:
faster HTTP shutdown polling, five-agent adapter parity, no unused preflight
roster, and one asserted delegation agent. The tested production paths and
assertion sets are unchanged.

## Challenges encountered

The first green instrumented run exposed useful file costs but its v1 artifact
did not bind enough provenance to generate release-quality weights. It remains
diagnostic only. Independent review drove the v2 commit, partition, aggregate,
link, and post-run source checks. A later package invocation under concurrent
local load exceeded its wrapper timeout and is not used in the matched result;
the governed three-sample full-corpus comparison remains necessary.

## Decisions and alternatives

Source bytes remain the explicit control and universal fallback. Keeping stale
duration weights silently was rejected. Invalidating the profile after every
product edit was also rejected because it would remove acceleration during the
normal development loop; the observable compatible state preserves utility
without allowing strict benchmark claims.

## Verification

- Profile, runner, and sharding contracts: 52 passed warning-strict.
- Matched fixture-cost package: 77 passed, 5 skipped; 84.38 seconds before and
  48.06 seconds after, saving 36.32 seconds (43.04 percent) on local Windows.
- Independent timing-layer review approved the v2 producer through loader chain.
- Documentation metadata, policy availability, worklog, and docs checks passed.
- Ruff, format, and Git diff checks passed.

## Follow-ups

Capture three clean v2 source-byte controls from this evidence commit, generate
the versioned Windows profile, and run matched strict-profile samples plus a
one-worker control. Do not recommend the parallel loop until the median
full-corpus improvement reaches AR-156's unchanged 30 percent gate.
