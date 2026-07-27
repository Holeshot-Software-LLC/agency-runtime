---
title: "AR-182: Bind Codex hook trust guidance to the generated inventory"
status: done
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [codex, hooks, installation, documentation, correctness]
related:
  - agency_runtime/core/installer_contracts.py
  - agency_runtime/core/installer_payloads.py
  - agency_runtime/core/smoke.py
  - tests/test_native_installer.py
  - docs/TROUBLESHOOTING.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/issue-AR-105-current-codex-hook-event-count.md
supersedes:
  - docs/roadmap/issue-AR-105-current-codex-hook-event-count.md
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-182
priority: p1
tracker_url: null
depends_on: []
blocks:
  - AR-180
---

# AR-182: Bind Codex hook trust guidance to the generated inventory

## Problem

Codex's generated bundle contains eight Agency Runtime hook events after
`PreToolUse` was added for native-child specialist binding. Installer and
operator guidance still reported the earlier seven-event contract, so an
operator could not reliably compare the trust prompt with the exact bundle.

## Current state

The generated bundle and smoke validator already require `SessionStart`,
`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `SubagentStart`,
`SubagentStop`, `PostCompact`, and `Stop`. The canonical installer contract now
owns that ordered inventory and derives both the count and names in the trust
instruction. Payload construction and smoke validation bind to the same tuple.
Tracker creation remains pending explicit outward-write authorization.

## Approach

Own the ordered Codex hook inventory in the dependency-light installer contract.
Use it to build exact operator guidance, fail payload construction on inventory
drift, and validate the generated bundle. Preserve AR-105 as faithful evidence
of the earlier seven-event contract while making AR-182 the current owner.

## Dependencies

AR-180 owns the exact installed-bundle activation canary. AR-105 records the
historical correction from three to seven events.

## Acceptance

- [x] One ordered constant owns all eight generated Codex hook event names.
- [x] Installer and status guidance derives its count and exact names from that
  inventory.
- [x] Generated payload construction and smoke validation fail on inventory
  drift.
- [x] Maintained troubleshooting and release guidance reports the current eight
  events without rewriting faithful historical evidence.
- [x] Focused tests, Ruff, documentation validation, and diff validation pass.

## Implementation evidence

The canonical event tuple now drives the derived count and exact names in the
operator instruction, binds payload order, and replaces the smoke validator's
independent duplicate. The focused native-installer and smoke package passes 35
tests. Ruff check and formatting pass for every changed Python file; metadata,
documentation, and diff validation pass for the complete change.
