---
title: "Bind native hooks to authoritative master control"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [runtime-control, hooks, codex, claude, windows, security]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: b8f80bd5a6993e2358361dbfa6ee167403033b4a
short: b8f80bd
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114
related_issues:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
---

# Worklog detail: Bind native hooks to authoritative master control

## Purpose

Close the native-only canary defect that remained after projecting the disabled
state into the isolated host environment. Codex did not preserve that capability
for its hook subprocess, so routing and finalization evidence still appeared
while the real global switch was off.

## Approach

Generate Codex and Claude hook commands with the installer-owned absolute
`--runtime-control` identity alongside `--config`. Read that bound identity
before input parsing or Store construction. Direct owner-private validation stays
primary; a positively identified restricted Windows hook may recover only the
complete validated master document through the authenticated local dashboard.

## Challenges encountered

The first interrupted edit misplaced the enforcement reader's exception block
and forwarded the new argument to MCP instead of the hook entrypoint. Focused
contract tests exposed both mistakes before commit. The hook environment itself
was insufficient as the durable boundary because Codex did not propagate it.

## Decisions and alternatives

An environment-only capability was retained for hosts that preserve it but is
not trusted as the sole enforcement path. Arbitrary explicit paths, unauthenticated
brokerage, and permissive failure were rejected. Invalid paths, ordinary access
failures, malformed dashboard results, and unavailable brokerage all fail
enabled.

## Verification

- Runtime-control, hook, CLI, installer, and adapter parity: 430 passed, 4 skipped.
- Complete canary-mode, cohesion, runtime-control, and hook integration: 234
  passed, 4 skipped.
- Ruff check and format, metadata, policy availability, worklog consistency,
  documentation validation, and patch-integrity checks passed.

## Follow-ups

Build and install an exact artifact from this commit, then repeat both guarded
Codex canary modes. Native-only must emit no header, no Agency evidence, and no
attestation before AR-111 can close.
