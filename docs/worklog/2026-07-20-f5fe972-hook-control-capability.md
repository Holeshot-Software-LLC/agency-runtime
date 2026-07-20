---
title: "Bind isolated hook subprocesses to canary control"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [canary, runtime-control, codex, windows, security]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: f5fe9724d8a355d7fbf79fcf57bb922e0dba6f00
short: f5fe972
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114
related_issues:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
---

# Worklog detail: Bind isolated hook subprocesses to canary control

## Purpose

Close the deeper boundary exposed by the first exact native-only canary. Codex
returned no Agency header, but its hook subprocess still produced a run, one
routing decision, and two finalizations because the subprocess did not resolve
the projected isolated master-control path.

## Approach

Publish the already validated projected control file's absolute path in the
isolated canary environment. Resolve that path only when canary mode is
explicitly active, require the canonical `.agency-runtime/run/control.json`
suffix, retain explicit API path/home precedence, and keep normal processes on
the canonical per-user path.

## Challenges encountered

Header exclusion alone looked correct, but zero-evidence validation caught the
partial bypass. The correlated trace proved UserPromptSubmit routing and Stop
finalization still ran, and its resident-manager binding reported an absent
master generation. The guarded trial restored the real master switch to enabled
generation 12 before diagnosis continued.

## Decisions and alternatives

An unvalidated general environment override was rejected. The selected
capability is canary-only, absolute, canonical-suffix constrained, and still
subject to the runtime-control file's owner/private-path validation.

## Verification

- Runtime-control and canary regression suite: 151 passed, 4 skipped.
- Codex and Claude backend tests prove the projected path and enabled value are
  present in their isolated environments.
- Negative tests prove relative/noncanonical paths fail and normal runtime mode
  ignores the override.
- Ruff check/format, documentation links, and patch-integrity gates passed.

## Follow-ups

Rebuild the exact artifact and repeat both live canary modes under
[AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md).
