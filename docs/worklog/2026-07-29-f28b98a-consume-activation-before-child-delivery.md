---
title: "Worklog detail: Consume Codex activation before child delivery"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, activation, hooks, ordering]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: f28b98a
short: f28b98a
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Consume Codex activation before child delivery

## Purpose

Persist the opaque Codex canary activation against the real child lifecycle
before returning exact specialist context from SubagentStart.

## Approach

After persisting the native child UUID, SubagentStart consumes the exact
native-hook grant using its tool-use, unit, specialist version, prompt hash,
worker, and native-run identities. It returns specialist context only when the
stored receipt matches every delivery field. PostToolUse remains idempotent.

## Evidence

Exact-installed PR 164 repeatedly selected, spawned, waited for, and completed
one `code-reviewer` child with a valid header but no activation receipt. Bounded
capture proved the spawn output contained only the rooted task name; the
apparent rollout errors were isolated trust-bypass notices.

## Verification

- Two exact activation-chain tests passed.
- Ruff check and format passed for the changed source and test.
- Documentation validation passed for 517 Markdown files.

## Follow-ups

Refresh the Codex launcher from this checkpoint, prove the source live canary,
then run the named fast spine before PR and exact-install verification.
