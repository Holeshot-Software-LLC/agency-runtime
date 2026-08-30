---
title: "Worklog: Isolate native host lifecycle CWD"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [security, host-integrations, processes, codex]
related:
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
  - docs/worklog/README.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0106-isolate-native-host-lifecycle-working-directories.md
supersedes: []
superseded_by: null
type: worklog
commit: 63a1f5f
short: 63a1f5f
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
---

# Worklog detail: Isolate native host lifecycle CWD

## Purpose

Allow exact native host inspection and prepared Codex refresh to run from a
broad non-repository directory such as the user's home without misclassifying a
legitimate user-installed host CLI as repository content.

## Approach

Ordinary native lifecycle calls now allocate one owner-private ephemeral
working directory and use it consistently for PATH sanitization, executable
preparation, identity freezing, and child execution. Marker-only ambient root
discovery preserves every real repository ancestor. The prepared Codex refresh
uses the existing validated private Agency runtime root and discovers the bare
Codex command through the same sanitized, identity-frozen boundary.

## Challenges encountered

The first installed artifact failed safely before mutation because the ambient
home was recursively forbidden. Independent review then found two incomplete
fix shapes: child PATH still used the ambient CWD, and moving only the launch
directory could re-admit a repository sibling executable. Both were corrected
before commit, and the separate prepared-refresh path received the same
boundary.

## Decisions and alternatives

Globally relaxing current-directory exclusion and special-casing the user's
home were rejected because both weaken repository poisoning defenses. ADR-0106
records the private-CWD plus marker-derived ambient repository design.

## Verification

- Boundary-focused warning-strict package: 98 passed, 1 platform skip.
- Named production/security spine: 522 passed, 5 platform skips in 60.55
  seconds.
- Dashboard UI: 106 passed.
- Routing, policy, delegation, performance, scale, and CLI startup gates passed.
- Ruff, formatting, 475-document validation, worklog, and diff checks passed.
- Live read-only prepared Codex discovery proved `codex-cli 0.145.0` from the
  owner-private runtime CWD and froze the canonical native executable identity.

## Follow-ups

Build and install the exact checkpoint, complete the attended existing-Codex
refresh, and run one fresh current-profile activation verification under
AR-187/AR-185. Tracker creation remains pending outward-write authorization.
