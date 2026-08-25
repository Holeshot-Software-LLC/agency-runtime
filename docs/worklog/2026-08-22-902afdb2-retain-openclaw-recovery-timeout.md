---
title: "Retain OpenClaw recovery timeout"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, finalization, timeout, evidence]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
supersedes: []
superseded_by: null
type: worklog
commit: 902afdb256acaa41b81037b9489445c17e03d0fe
short: 902afdb2
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md
---

# Worklog detail: docs(roadmap): retain OpenClaw recovery timeout

## Purpose

Preserve the first changed post-AR-278 live result before another evaluation,
without promoting successful Agency preflight into native response delivery.

## Approach

Record the Agency-only install identity, exact profile/provider/alias evidence,
zero fallback, selected specialists and skill, then separately record the
unchanged native host's 240-second timeout and absence of `agency_finalize`, a
five-line header, terminal Store finalization, or Telegram delivery.

## Challenges encountered

The Agency router completed all three inference stages, but OpenClaw's native
`task-general` model continued through 31 successful read-only tool calls until
its provider budget expired. Store run `6726b5ce...` therefore remains
active/ready rather than carrying a terminal finalization receipt.

## Decisions and alternatives

Do not retry the same input, change OpenClaw's native model configuration,
reinterpret an active Store run as success, or add a correction pass forbidden
by ADR-0120. Preserve the timeout, then use a genuinely changed prompt whose
only permitted tool is the existing finalizer.

## Verification

Documentation metadata, policy availability with checkout import resolution,
worklog consistency, documentation validation, handoff size, and
`git diff --check` pass before the recovery commit.

## Follow-ups

Run the tighter fresh-session proof after immediate context telemetry. Then
take the post-live SQLite backup, correlate exact Store and host evidence, and
run proportionate final gates under
[AR-278](../roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md).
