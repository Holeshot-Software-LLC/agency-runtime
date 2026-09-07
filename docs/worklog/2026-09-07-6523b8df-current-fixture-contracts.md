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

## Current complete package

49b307ff (49b307ff3ae7d248bee0b7135d5b0843daa9b1de) repairs the main-reproduced retained-stage fixture using real guarded cleanup. Seven focused cases pass; combined package 467 passes/one skip/64 Windows-named deselections, named spine 1085/three skips, UI 224/current floors and Node smoke contracts 36 pass. Existing ADR-0105/0224 reconcile only obsolete exhaustive gates; faithful July criteria and red diagnostics remain. Runtime bytes equal the AR-175 installed artifact source a96483ad.

## Frozen current candidate

9a42c162 (9a42c1627e4cd6bd6002833c83b093ba6c72c6a7) freezes eight builder-only criteria at 49b307ff. Dry-run checks confirm every cited excerpt is included (1,512–16,303 characters per packet). The original verdicts have not run yet. AR-388's documented owner-private client environment exists and contains the configured variable; this changed precondition permits a new bounded native check without provisioning or persisting a key.
