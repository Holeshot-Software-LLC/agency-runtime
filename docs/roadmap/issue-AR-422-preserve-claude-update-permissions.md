---
title: "AR-422: Preserve Claude executable permissions across npm updates"
status: in_progress
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, native, staffing]
related:
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-422
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/809
depends_on: []
blocks: []
---

# AR-422: Preserve Claude executable permissions across npm updates

## Problem

Claude npm-global updates repeatedly recreate group-writable executable parents. The latest update receipt and process umasks explain the recurrence; the normal Agency gate correctly refuses the executable.

## Current state

Phase implementing. The offline npm fixture reproduces writable package parents;
config mask022 alone still leaves the package root and executable775. No npm
user configuration was changed. Supported `claude install 2.1.266` under umask077
now provides the native launcher and versioned binary; parent directories700,
normal Agency executable gate passes and normal refresh returnsok. Existing npm
processes and user terminals remain intact. A second supported same-version install under process002 preserves the exact
binary and normal trust. Native answering and isolated acceptance remain. Evidence:
[evidence/AR-422-claude-native-install-20260909.json](evidence/AR-422-claude-native-install-20260909.json).

## Approach

An offline npm fixture shows an npm config mask alone does not secure the package root and executable. Use a supported native installation path under restrictive creation permissions, verify the normal executable gate and native lifecycle, and leave existing user terminals intact.

## Dependencies

AR-404 retains the complete five-host reliability sample and all-host gates.

## Acceptance

- [ ] Reproduce the observed failure with exact, bounded evidence.
- [ ] Repair its cause while preserving trust, inference authority and unrelated work.
- [ ] Verify the repaired behavior with regression/native evidence and isolated verdicts.
