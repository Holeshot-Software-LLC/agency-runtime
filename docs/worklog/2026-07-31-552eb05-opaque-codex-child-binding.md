---
title: "Worklog detail: Bind opaque Codex children to exact plan rows"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [codex, delegation, activation, security, evidence]
related:
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 552eb05
short: 552eb05
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
---

# Worklog detail: Bind opaque Codex children to exact plan rows

## Purpose

Remove the fixed-canary exception that let Codex activation pass while every
arbitrary product specialist launch failed before child start. Retained product
traces proved that Codex exposes the native collaboration message to
`PreToolUse` as ciphertext, so exact plaintext goal comparison cannot work at
that boundary.

## Approach

Keep plaintext child launches on the v1 exact-goal contract. For opaque Codex
launches, require the unencrypted task label to resolve exactly one accepted
persisted row, preserve the host ciphertext byte-for-byte, stage that row's
one-use grant, and inject a token-free v2 specialist context at
`SubagentStart`. The v2 context binds the immutable specialist identity,
work-unit ID, prompt hash, and persisted goal hash to the observed child.

Product projection now reads the authenticated v2 goal hash directly without
retaining the task, ciphertext, specialist prompt, tool traffic, or child
result. External-write rows remain denied and workspace-write rows remain
inside the disposable product workspace.

## Challenges encountered

The passing fixed activation canary concealed the real product boundary. Two
historical Codex traces and the consumed `584b949` trial were needed to
separate successful inference and plan publication from the subsequent native
spawn rejection. Current Codex hook events do not expose the decrypted task or
a host-authenticated task digest, so ADR-0127 records the strongest observable
binding and its explicit limitation.

## Decisions and alternatives

ADR-0127 governs the Codex-specific content-free v2 contract. Rewriting the
encrypted block, retaining a canary-only exception, inventing resource paths
from hashes, and accepting an opaque launch without an exact persisted label
were rejected.

## Verification

- 97 focused warning-strict tests passed, including a real SQLite Store
  arbitrary-goal lifecycle and product rollout projection.
- Both new opaque-child decision mutations were killed with unchanged source.
- Focused Ruff lint and formatting checks passed.
- Documentation validation passed for all 592 Markdown files.
- The named fast production spine remains the next gate.

## Follow-ups

Complete AR-209's named fast gate, reviewed merge, exact install, and one fresh
activation plus product trial before treating the README story as proven.
