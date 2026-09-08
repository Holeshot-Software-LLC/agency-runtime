---
title: "AR-251 test the section bound independently of card decoration"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [cli, verification]
related:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
  - docs/roadmap/handoffs/issue-AR-251.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues: [docs/roadmap/issue-AR-251-cli-presentation-richness.md]
---

# AR-251 test the section bound independently of card decoration

## Purpose

Correct a new regression's mistaken whole-card byte limit without changing the
renderer or loosening its actual section-content assertion.

## Approach

The shared renderer limits a section to 4096 bytes, excluding Unicode dividers,
labels and truncation guidance. Assert exactly 4095 retained ASCII value bytes
and no rendered line beyond 4096 bytes; retain the explicit truncation notice
and absence of the complete 5000-byte value.

## Challenges encountered

The combined focused run reported 1 failed, 371 passed and 1 skipped in 39.47s.
The entire decorated card was 5317 bytes, so the invented less-than-5000-byte
whole-card assertion failed even though the value was correctly bounded.

## Decisions and alternatives

No runtime or presentation policy change. Do not shrink user-visible content
merely to satisfy an incorrect assertion or hide the initial failure.

## Verification

After this test-only change, all 61 card tests passed in 0.42 seconds. Ruff and
diff checks passed. The combined production spine independently passed 1151
cases with three skips in 69.91s; it does not include this focused card file.

## Follow-ups

Parent publishes the final delivery branch, installs exact main and records a
real CLI demonstration. Tracker #260 remains open for isolated acceptance.
