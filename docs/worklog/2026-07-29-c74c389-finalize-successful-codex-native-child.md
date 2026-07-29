---
title: "Worklog detail: Finalize successful Codex native child"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, activation, callbacks, delegation, finalization]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c74c389
short: c74c389
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Finalize successful Codex native child

## Purpose

Close the final Codex activation-canary gap after selection, activation,
specialist loading, real-child lineage, spawn, and wait evidence were already
proven live.

## Approach

Treat a non-empty Codex SubagentStop `last_assistant_message` as the host's
successful child-turn completion edge. The hook records only `outcome=ok`
against the exact correlated child identity and never persists the message.
Empty stops retain the existing outcome-free projection. The expected
PostToolUse-before-SubagentStart activation gap no longer produces a stale
canary rejection.

## Challenges encountered

Trace `019faf17-be08-75a1-a074-8425eff20a71` was fully proven except for the
authoritative finalization. It showed that the successful native child had
ended while the Store still held an unset exit code and a delegated status.

## Decisions and alternatives

The repair uses Codex's explicit child final-message signal rather than
interpreting the generic wait response. An empty or missing message cannot
fabricate success, and Claude's separate outcome-free lifecycle remains
unchanged.

## Verification

- All 20 Codex activation-canary tests passed.
- All 33 cross-host native-child hook tests passed.
- Changed-file Ruff check and format, documentation validation, and diff checks
  passed.
- The broader activation-receipt rerun reached its existing no-output timeout;
  the preceding focused checkpoint passed 35 tests with two platform skips.

## Follow-ups

Run the source-live isolated canary, named fast spine, PR and merge flow, exact
install, and fresh Codex proof under AR-199.
