---
title: "Grant OpenClaw Agency prompt injection"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, installer, prompts, agency]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
supersedes: []
superseded_by: null
type: worklog
commit: b4c27089dd379db9fb84cf3a8da86bd3eb03cfca
short: b4c27089
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md
---

# Worklog detail: fix(openclaw): grant agency prompt injection

## Purpose

Permit the installed Agency OpenClaw plugin to inject its already-completed
preflight context into the native model prompt on audited OpenClaw 2026.7.1-2.
Without this permission, the Store reached preflight `ready` but OpenClaw
reported zero runtime-context characters and canonical finalization failed.

## Approach

Add one supported, plugin-owned registration command after conversation access:
`plugins.entries.agency-preflight.hooks.allowPromptInjection=true`. Record the
same command in the dry-run plan and treat failure as an exact registration
step that enters the existing final-only delivery rollback. No generated hook,
native model, provider, fallback, channel, alias, or protected host changes.

## Challenges encountered

The free 9B alias target produced valid schemas but inconsistent semantic
results. The already-installed 30B coder target accepted the exact Agency-only
request, isolating the next failure to native prompt delivery. The first broad
test run inherited umask `0002` and correctly failed trusted-namespace checks;
the unchanged suite passed under process-local umask `0077`.

## Decisions and alternatives

Use OpenClaw's current supported permission instead of returning preflight to
the non-blocking prompt hook, using deprecated `before_agent_start`, disabling
Agency, or weakening finalization. Keep configured LiteLLM alias identity
separate from unavailable actual-model telemetry.

## Verification

Expected-red retained one command-plan failure before repair. After repair,
`tests/test_installer_registration.py` passes 46/46 warning-strict. The focused
OpenClaw installer, adapter, and delivery-policy slice passes 127 with one skip.
Documentation validation passes for 750 files; full Ruff lint and format checks
pass for 682 Python files; `git diff --check` passes.

## Follow-ups

Stop OpenClaw natively, reinstall Agency only from this checkpoint, restart,
and require fresh Store-backed header/finalization evidence under
[AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md).
