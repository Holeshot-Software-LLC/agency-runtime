---
title: "Preserve native finalization attribution"
status: active
category: worklog
created: 2026-08-23
updated: 2026-08-23
tags: [openclaw, hermes, finalization, correlation]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-274-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
supersedes: []
superseded_by: null
type: worklog
commit: 21f2519d357b0f40892aba2d567fd97fccb23d8d
short: 21f2519d
date: 2026-08-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-274-record-openclaw-native-skill-reads.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
---

# Worklog detail: Preserve native finalization attribution

## Purpose

Repair two runtime-owned attribution losses found by fresh OpenClaw and Hermes
status turns without changing either host's native model configuration.

## Approach

OpenClaw's bounded, collision-safe, expiring, one-use tool correlation now
carries the preflight model into the awaited tool-result refresh. The bridge
uses that model only for the Store-backed updated header. Generic MCP
finalization derives its host from the exact Store-owned run when session and
trace match, otherwise retaining `mcp`.

## Challenges encountered

OpenClaw's native transcript contained a response, but the final-only gate
correctly withheld it because its refreshed header said `none observed`.
Hermes completed but exposed the independent hard-coded `mcp` attribution. A
broad focused batch first hit a shared pytest directory mode of `0775`; the
documented process umask `0077` restored its required private boundary.

## Decisions and alternatives

No host configuration, provider route, response-rewrite pass, or
caller-supplied host field was introduced. The fixes preserve existing safety
and correlation boundaries and remain model-agnostic.

## Verification

- Both focused regressions failed before implementation and passed afterward.
- Affected host/finalization slice: 232 passed, 6 intentional skips.
- Focused Ruff check and format check passed.
- Documentation metadata, generated-policy, worklog, verification, and diff
  checks passed before the substantive commit.

## Follow-ups

Reinstall Agency only into both hosts, then use changed fresh turns to prove
delivery, native-host attribution, and Hermes-scoped `task-agency-router`
workforce inference. Rule 4 native-child delivery remains unproven.
