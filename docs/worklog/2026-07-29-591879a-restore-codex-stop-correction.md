---
title: "Worklog detail: Restore Codex Stop correction continuation"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, hooks, stop, finalization, continuation]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 591879a
short: 591879a
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Restore Codex Stop correction continuation

## Purpose

Deliver the authoritative post-child header correction to Codex instead of
terminating the Stop hook before the model can revise its stale preflight
header.

## Approach

Corrective Stop outcomes now use Codex's documented `decision: "block"` shape,
which creates one continuation prompt from the bounded reason. Terminal retry
exhaustion retains `continue: false`. ZCode's always-block compatibility rule
is unchanged. The PostToolUse path also initializes optional child identity
before branching so ordinary non-spawn tools cannot read an unbound local.

## Challenges encountered

Trace `019faf3e-5eb6-7a92-9423-cb5b083fa285` showed that selection, activation,
child execution, and delegation completion were correct while six dynamic
header fields remained at their pre-child values. The persisted mismatch codes
distinguished a missing correction pass from missing runtime evidence.

## Decisions and alternatives

Follow the current Codex Stop schema directly: `decision:block` requests a
correction, while `continue:false` is reserved for terminal fail-closed
outcomes. Do not weaken header verification or pre-author the post-child header
before its evidence exists.

## Verification

- All 87 native hook tests passed.
- Both Codex and Claude retry/terminal replay cases passed.
- The adjacent finalization, security, and resident-manager run passed 83 tests
  before the outdated Codex shape assertion; its exact two-host rerun passed.
- Changed-file Ruff check and format, documentation validation, and diff checks
  passed.

## Follow-ups

Run the source-live isolated canary and require an authoritative accepted
attestation before the fast spine and PR.
