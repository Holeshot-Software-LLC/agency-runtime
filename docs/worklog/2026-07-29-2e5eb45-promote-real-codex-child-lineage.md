---
title: "Worklog detail: Promote real Codex child activation lineage"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, activation, callbacks, delegation, store]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 2e5eb45
short: 2e5eb45
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Promote real Codex child activation lineage

## Purpose

Repair the live Codex callback order in which parent PostToolUse records a
synthetic task identity before child SubagentStart consumes the exact activation
grant against the real child UUID.

## Approach

The existing activation-attachment transaction now permits one narrowly scoped
promotion. It requires Agency's exact generated Codex task label, the planned
specialist, a consumed native-hook grant, and exactly one matching
`codex-agent:<UUID>` lifecycle row. The same transaction replaces the synthetic
delegation lineage, links the activation receipt, and binds the worker row to
the work unit. Every incomplete, ambiguous, non-Codex, or lookalike lineage
retains the prior fail-closed behavior.

## Challenges encountered

The production callback order was the reverse of the original test helper. A
Store-backed fixed-code diagnostic and trace
`019faef8-f76b-7740-9558-462e99f4abeb` were required to distinguish temporal
ordering from missing selection or lost activation evidence.

## Decisions and alternatives

The repair lives in the existing atomic attachment boundary rather than adding
a second hook-only rewrite. This makes both callback orders converge under the
same transaction and avoids weakening the bounded PostToolUse response parser.

## Verification

- All 20 Codex activation-canary tests passed.
- All 35 activation-receipt tests passed with two platform skips.
- Changed-file Ruff check, format, documentation validation, and diff checks
  passed.

## Follow-ups

Run the source-live isolated canary, named fast spine, PR and merge flow, exact
install, and fresh Codex proof under AR-199.
