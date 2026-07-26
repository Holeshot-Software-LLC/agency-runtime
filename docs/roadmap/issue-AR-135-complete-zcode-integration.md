---
title: "AR-135: Complete ZCode native integration end to end"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [host-integrations, zcode, installer, hooks, evidence]
related:
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - agency_runtime/core/installer_payloads.py
  - agency_runtime/core/installer_registration.py
  - agency_runtime/adapters/hooks.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-135
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-135: Complete ZCode native integration end to end

## Problem

The CLI documents ZCode as supported, but fresh install produces a Claude
bundle, registration raises `KeyError("zcode")`, control planning falls through
to Claude commands, and its post-tool path cannot consume or attribute the
specialist prompt inserted by its pre-tool path.

## Current state

The dedicated `zcode_hooks()` renderer is unreachable. ZCode is absent from
activation-consumption host constraints and some canonical tool/worker maps.
Status inspects staged files rather than the active ZCode config-hook
registration. Failure hooks are incomplete.

## Approach

Use one canonical five-host registry across bundle generation, native command
planning, registration, inventory, controls, activation consumption, tool
identity, pre/post/failure hooks, lineage, status, smoke, and UI presentation.
Merge the exact ZCode config reversibly and prove postconditions.

## Dependencies

AR-134 owns the schema migration. AR-131 owns shared MCP schemas. AR-136 owns
cross-process child correlation.

## Acceptance

- Fresh, idempotent ZCode install writes and merges only canonical ZCode files.
- Registration, enable/disable, rollback, status, and smoke have exact
  postconditions and no Claude fallback.
- PreToolUse through PostToolUse or failure consumes one activation and records
  `zcode-agent:*` lineage.
- Every claimed ZCode hook event has the documented host-native response shape.
- Tests cover fresh home, existing config preservation, rollback, and drift.
