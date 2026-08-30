---
title: "Worklog detail: Deliver authoritative ZCode parent headers"
status: active
category: worklog
created: 2026-08-19
updated: 2026-08-19
tags: [zcode, headers, host-parity, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
supersedes: []
superseded_by: null
type: worklog
commit: 88fc19566e6c84b55650509d3d0c9d959d49dc4f
short: 88fc1956
date: 2026-08-19
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: Deliver authoritative ZCode parent headers

## Purpose

Make ZCode receive the same exact current-turn, Store-backed parent header that
the Stop hook enforces for Claude and Codex. The merged-main attended smoke had
correctly rejected ZCode after it saw only placeholder fields and consequently
misreported both loaded Agency context and Agency-observed model execution.

## Approach

Generalize the shared header-snapshot helper name and admit ZCode to its existing
initial and updated parent-response paths. Preserve every native child lifecycle
branch unchanged. Extend subprocess-shaped initial/Stop coverage and post-tool
coverage to ZCode, and strengthen the routed ZCode proof to require the exact
snapshot marker and Store-derived loaded/model fields.

## Challenges encountered

The ZCode parent ran through GLM-5.3 while Agency's separate workforce inference
ran through Claude Sonnet. Store finalization, host model I/O, and hook context
had to be correlated so the repair addressed the missing evidence snapshot
rather than incorrectly pinning or relabeling the ambient parent model.

## Decisions and alternatives

An operator-authored prompt containing the expected header values was rejected
as proof because it would make the validator pass without proving the installed
harness delivered those values. The updated snapshot also remains enabled after
ZCode parent tool use so later skill or execution evidence cannot leave its
final header stale.

## Verification

- Focused initial-header, updated-header, and ZCode lifecycle checks: 7 passed.
- Widened hook, ZCode proof, and adapter-parity suite: 144 passed.
- Repository local fast harness: 12/12 gates passed in 1.3 minutes.
- Focused Ruff check/format, documentation contracts, and `git diff --check`:
  passed.

## Follow-ups

Fresh owner authority is required to push, open and merge a second PR, reinstall
from the resulting exact `main`, and run the one attended ZCode parent smoke
tracked by [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md).
