---
title: "Worklog: Reduce stable routing startup work"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [performance, routing, roster, cli]
related:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 0c0299a41f75455dce77cb477c282243fe664c90
short: 0c0299a
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
---

# Worklog: Reduce stable routing startup work

## Purpose

Remove measured redundant work from stable operational routing and make the
module-form version command use the already established lazy CLI entrypoint.

## Approach

Added a bounded exact-slug Store query that retains the complete active-worker
join and decoder for the two fallback identities. After package reconciliation,
the operational path reads the trusted monotonic roster generation and reuses
its coherent initial snapshot only when that generation is unchanged.
`python -m agency_runtime.cli` now delegates to the same deferred-import
dispatcher as the package console script.

## Challenges encountered

Snapshot reuse could not rely on reconciliation return counts because contract
projection repairs and concurrent roster changes also affect routing. The
existing roster generation is the authoritative coherence boundary, and every
change still forces a complete recapture.

## Decisions and alternatives

No positive filesystem or authorization cache was introduced. A fast slug-only
projection was rejected because malformed active definitions must not count as
usable fallbacks; the bounded query therefore retains all canonical joins and
decoding. Stable contractor reconciliation remains intentionally visible for a
separate measured slice.

## Verification

- Complete affected suites: 104 passed.
- `python -m` version median: about 647 ms to 112 ms.
- Fallback presence check: 233.371 ms to 22.453 ms.
- Stable operational snapshot: 1,104.677 ms to 663.671 ms.
- Ruff check, format check, documentation validation, and diff check: passed.

## Follow-ups

AR-140 remains open for the 400-450 ms stable contractor reconciliation, the
1.585-second 276-query no-op starter path, supported-runner performance
evidence, and a fresh installed console-script check.
