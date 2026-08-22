---
title: "Preflight OpenClaw during prompt build"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, prompts, lifecycle, agency]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
supersedes: []
superseded_by: null
type: worklog
commit: d9a1a7ce727fe45d7a0ea0826e75a2eb460c83b7
short: d9a1a7ce
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
---

# Worklog detail: fix(openclaw): preflight during prompt build

## Purpose

Deliver Agency's Store-backed preflight context into the OpenClaw prompt while
retaining a fail-closed gate before any native model call. A permission-enabled
fresh turn still reported zero runtime-context characters because Agency
modeled the installed hook lifecycle in reverse.

## Approach

Run runtime control and the existing exact preflight in
`before_prompt_build`, cache the bounded result by exact session and run, and
return it as `appendContext`. Keep `before_agent_run` as the enforcement gate:
it rechecks runtime and delivery safety and passes only when the exact context
already exists. A swallowed prompt-hook failure therefore still blocks before
provider execution.

## Challenges encountered

Granting OpenClaw's supported `allowPromptInjection` permission did not change
the live symptom. Inspection of the installed 2026.7.1-2 runner established
that prompt construction completes before `before_agent_run`; the generated
test had explicitly invoked those hooks in the opposite order. This isolated
the defect from the free model behind `task-agency-router`.

## Decisions and alternatives

Use the current non-deprecated prompt hook for context and the later input gate
for enforcement. Do not weaken finalization, fall back to an ungoverned native
turn, change OpenClaw's `task-general` route, or bind Agency behavior to the
current LiteLLM backing model.

## Verification

The corrected real-order regression failed before repair at exit 204. After
repair, all 46 security-boundary tests pass. Focused native-installer,
adapter-parity, host-boundary, and registration slices pass 36, 24, 1, and 46
tests. Focused Ruff lint/format, documentation validation, metadata/worklog
checks, and `git diff --check` pass.

## Follow-ups

Reinstall Agency only into stopped OpenClaw, restart natively, and require a
fresh Store-backed header and finalization before claiming native or Telegram
delivery under
[AR-276](../roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md).
