---
title: "Normalize hook-control portability contracts"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [testing, portability, linux, windows, runtime-control]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: cb17e0d0bfbf26d31ba02f664ea224dc6fd32054
short: cb17e0d
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114
related_issues:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
---

# Worklog detail: Normalize hook-control portability contracts

## Purpose

Repair four Ubuntu matrix failures exposed after the authoritative hook-control
fix while preserving the already proven Windows runtime behavior.

## Approach

Make canary path assertions compare `Path.parts` instead of a Windows separator,
extend a private installer facade double for the new control argument, and inject
restricted-token evidence directly without mutating the process-wide `os.name`.
The production broker still receives the real platform bit.

## Challenges encountered

All five Ubuntu versions failed from the same test-only assumptions. Mutating
`os.name` caused `pathlib` and dashboard imports to behave as Windows while still
running on POSIX, hiding the intended broker test behind a fail-enabled result.

## Decisions and alternatives

No product threshold or security check was weakened. The platform flag remains
derived inside production code; tests replace only the bounded token probe and
use separator-independent path semantics.

## Verification

- Exact four hosted failures plus brokerage variants: 6 passed.
- Expanded canary, runtime-control, hook, and private-coverage suite: 300 passed,
  4 skipped.
- Ruff check and formatting passed.

## Follow-ups

Rerun the complete hosted Windows/Linux matrix from this commit.
