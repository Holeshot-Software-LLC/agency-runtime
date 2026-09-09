---
title: "AR-422: Preserve Claude executable permissions across npm updates"
status: done
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

Done for the executable installation repair. The offline npm fixture reproduces
writable package parents; config mask022 alone is insufficient. Supported
`claude install 2.1.266` under umask077 provides a trusted native launcher and
versioned binary, with700parents and755executable. No npm user config, existing
process or terminal was changed. Normal Agency refresh succeeds.

A supported same-version reinstall under the original process002 preserves
the exact binary and normal executable trust. A fresh native review57.602s
proves exact code-reviewer delivery, five Store-matching headers and accepted
response hash. All three isolated acceptance criteria are satisfied.

This is same-version installation evidence, not a guarantee about future host
releases. Claude follow-up context limits remain AR-423, and its multi-step
staffing failure remains under AR-404. See
[evidence/AR-422-claude-native-install-20260909.json](evidence/AR-422-claude-native-install-20260909.json).

## Approach

An offline npm fixture shows an npm config mask alone does not secure the package root and executable. Use a supported native installation path under restrictive creation permissions, verify the normal executable gate and native lifecycle, and leave existing user terminals intact.

## Dependencies

AR-404 retains the complete five-host reliability sample and all-host gates.

## Acceptance

The repository-mandated isolated verdicts gate closure after these observable
criteria are judged; a criterion does not require its own verdict to pre-exist.

- [x] Reproduce the observed failure with exact, bounded evidence.
- [x] Repair its cause while preserving trust, inference authority and unrelated work.
- [x] Verify the repaired behavior with regression and fresh native evidence.
