---
title: "Worklog detail: Bind Codex hook trust inventory"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, hooks, installation, correctness]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
supersedes: []
superseded_by: null
type: worklog
commit: 4e39d4c1e5f2f7d4197a85c5562c4e38fb6f414c
short: 4e39d4c
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
---

# Worklog detail: Bind Codex hook trust inventory

## Purpose

Repair release-facing activation guidance that reported the earlier seven-hook
Codex contract after native-child `PreToolUse` binding expanded the generated
bundle to eight events.

## Approach

One dependency-light ordered tuple now owns the exact Codex hook inventory.
The terminal-TUI trust instruction derives its count and names from that tuple;
payload construction fails on order or membership drift; packaged smoke imports
the same owner instead of maintaining an independent set. AR-105 remains
faithful evidence of the historical seven-event contract, while AR-182 owns the
current eight-event contract.

## Challenges encountered

Generated smoke already knew about all eight events, so package smoke passed
while the separate human instruction and regression still asserted seven. The
repair therefore binds both machine and operator surfaces to one inventory
rather than updating another literal count.

## Decisions and alternatives

The installer continues to require approval through Codex's own terminal TUI;
Agency does not infer or mutate private hook-trust state. Numeric and exact-name
guidance is generated from the runtime tuple so future additions cannot silently
leave activation instructions stale.

## Verification

- Complete native-installer and smoke-isolation package: 149 passed.
- Focused Ruff check and formatting: passed.
- Documentation metadata and validation: 463 Markdown files passed.
- Diff validation: passed.

## Follow-ups

- Refresh the final exact Codex bundle only after the final artifact is built.
- An operator must approve all eight hooks in the Codex terminal TUI and run
  the AR-180 current-profile activation canary from a new task.
