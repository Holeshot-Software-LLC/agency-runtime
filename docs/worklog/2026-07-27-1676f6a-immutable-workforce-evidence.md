---
title: "Worklog detail: Cache immutable workforce evidence"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [performance, testing, workforce, mcp]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
supersedes: []
superseded_by: null
type: worklog
commit: 1676f6a07d94b2b1676d0720374697301836ad4b
short: 1676f6a
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
---

# Worklog detail: Cache immutable workforce evidence

## Purpose

Reduce repeated production-spine work without weakening a correctness,
security, or release gate and without moving expensive coverage back onto
automatic GitHub Actions.

## Approach

Canonical workforce serialization now uses a bounded 512-entry cache keyed by
the complete frozen contract and returns immutable bytes. The workforce-safety
suite memoizes its immutable roster projection once. The MCP direct-handler
test creates a real active and ready Store turn directly instead of invoking an
unrelated full cold preflight; every handler assertion remains unchanged.

## Challenges encountered

The cache had to preserve full mutation sensitivity and remain bounded. Its
regression therefore proves replacement creates a new value, the maximum size
is fixed, and an evicted contract is recomputed. Test setup changes were kept
separate from production preflight behavior so faster feedback could not mask a
preflight regression.

## Decisions and alternatives

Caching the complete immutable contract was selected over caching partial
fields or mutable dictionaries. Removing assertions, marking the tests as
integration-only, globally caching source state, and reordering production
preflight were rejected because they would reduce evidence or widen trust
scope.

## Verification

- The exact workforce hotspot fell from 5.45 to 2.66 seconds and the MCP
  hotspot from 4.08 to 0.81 seconds on the same Windows host.
- All 98 touched tests passed with one platform skip in 6.33 seconds.
- Ruff check and format, documentation validation, and `git diff --check`
  passed.
- No exhaustive Python corpus, compatibility matrix, hosted workflow, or push
  ran.

## Follow-ups

- Measure the named current-head production spine once after the remaining
  candidate scope is frozen under
  [AR-156](../roadmap/issue-AR-156-restore-cost-bounded-verification.md).
- Retain supported-runner and end-to-end performance evidence as open work under
  [AR-140](../roadmap/issue-AR-140-scale-routing-and-retrieval.md).
