---
title: "Worklog detail: accept exact 2 percent skill notice"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [codex, activation, host-notice, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 7ce640a36cd0eb74286976d712c7c7b23bc6215b
short: 7ce640a
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/199
related_issues:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
---

# Worklog detail: accept exact 2 percent skill notice

## Purpose

Accept the exact Codex 0.146 skill-catalog notice emitted by the installed host
without weakening the activation and product-proof unexpected-item gate.

## Approach

Add Codex's packaged `2% skills context budget` sentence as a second exact key
for the existing `skill_catalog_descriptions_shortened` content-free notice
type. Preserve the generic packaged sentence because the installed binary
contains both spellings. Exercise the current sentence through persisted
activation and multi-child product projections, while keeping both variants in
the exact parser test.

## Challenges encountered

Exact-installed activation completed routing, native delegation, accepted
finalization, and a zero-correction header, yet still failed because the live
sentence contained `2%` and the first repair admitted only the generic packaged
sentence. A bounded raw-JSONL diagnostic was needed to distinguish that exact
host wording from an unknown error.

## Decisions and alternatives

The repair enumerates the one observed packaged sentence. It does not use a
prefix, regular expression, percentage range, or blanket `error` acceptance.
Future unknown wording therefore continues to fail loudly. The existing
curated mutation still replaces the exact guard with arbitrary-error
acceptance and must be killed.

## Verification

- 25 warning-strict activation-canary tests passed.
- The named fast Python spine passed 636 tests with six skips.
- Dashboard UI passed 110 tests; documentation validated 584 files.
- Ruff checked and formatted 603 files; routing passed every gate.
- All 63 curated mutations were killed with zero survivors or invalid
  mutations, and source restoration passed.
- `git diff --check` passed.

## Follow-ups

Merge and exact-install this revision, prove one new-build activation canary,
then spend the single product trial tracked by
[AR-207](../roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md).
