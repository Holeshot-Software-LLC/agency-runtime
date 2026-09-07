---
title: "Align current evidence and trust fixtures"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [testing, evidence, security, backlog]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
type: worklog
commit: 6523b8dfc8071c12b843f29555d551b3be0b0c74
short: 6523b8df
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
---

# Worklog detail: test(runtime): align stale evidence and trust fixtures

## Purpose

Make the six carried stale cases test today's intentional runtime behavior
rather than restore removed fallback, public-delegation or retry policies.

## Approach

Repair three test boundaries: native event evidence, POSIX Store trust and
public routing. Preserve real ACL, owner, inode, link, replay, operator-prompt
and no-implicit-turn protections. No Python product changes.

## Challenges encountered

All six original cases fail on unchanged tests. The first repaired run passes
five, then the public-route case reaches another stale coordinator-seeding
expectation. Current inference-only policy makes that installation a no-op.
After correction all six pass in 2.30s.

The subsequent combined 14-module run reports 466 passed, one existing skip,
64 Windows-named deselections and one failure in 77.40s. The failing historical
installer fixture records cleanup instead of actually removing its stage;
the hardened product now detects that retained stage. Baseline reproduction
and a faithful cleanup double are the next bounded fix, not a runtime rollback.
This combined package is not green.

## Decisions and alternatives

Existing ADR-0105 and ADR-0224 govern bounded checks. Keep historical exhaustive
results as history, preserve the 97-percent floor, and do not dispatch an
unrequested exhaustive workflow. Source authority takes precedence over stale
agent-written expectations.

## Verification

Six repaired cases pass, focused lint/format and diff checks pass.
Combined package failure is explicitly recorded above. No new acceptance
verdict, aggregate coverage result or native activation is claimed.

## Follow-ups

Finish the combined fixture package, native output diagnostics, bounded
acceptance and normal PR/merge. Continue oldest-first until the owner's cutoff.

## Source checkpoint

6523b8df (6523b8dfc8071c12b843f29555d551b3be0b0c74) retains both focused red stages and the passing six-case repair. The combined installer fixture failure is preserved as unfinished work.
