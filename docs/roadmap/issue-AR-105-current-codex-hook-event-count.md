---
title: "AR-105: Report the current Codex hook event count"
status: done
category: roadmap
created: 2026-07-19
updated: 2026-07-19
tags: [documentation, codex, hooks, install]
related:
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
supersedes: []
superseded_by: docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
type: issue
epic: documentation
issue_id: AR-105
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/107"
depends_on: []
blocks: []
---

# AR-105: Report the current Codex hook event count

## Problem

Codex's generated plugin and smoke contract register seven Agency Runtime hook
events, but the installer trust guidance, README, and release checklist told
operators there were three. That stale count made the manual `/hooks` trust
step misleading and weakened release verification.

## Current state

The generated Codex bundle and its smoke validator require `PostCompact`,
`PostToolUse`, `SessionStart`, `Stop`, `SubagentStart`, `SubagentStop`, and
`UserPromptSubmit`. Maintained operator guidance now reports those as seven
Agency Runtime hook events. Historical canary records that faithfully observed
an earlier three-hook installation remain unchanged.

This record describes the seven-event contract at its implementation commit.
AR-182 owns the later eight-event contract after `PreToolUse` was added for
native-child specialist binding; historical evidence here remains unchanged.

## Approach

Use one accurate phrase in the installer contract and maintained documentation,
retain historical evidence unchanged, and bind the generated-install result to
the count with a regression assertion.

## Dependencies

None.

## Acceptance

- [x] Installer and status trust guidance reports seven Agency Runtime hook events.
- [x] README and release checklist match the generated bundle contract.
- [x] A regression test binds the guidance to the seven-event contract.
- [x] Focused tests and documentation validation pass.
