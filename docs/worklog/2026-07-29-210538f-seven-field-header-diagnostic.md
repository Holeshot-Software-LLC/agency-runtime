---
title: "Worklog detail: Derive the seven-field header diagnostic"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, headers, finalization, diagnostics]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 210538f
short: 210538f
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Derive the seven-field header diagnostic

## Purpose

Remove a contradictory Stop correction that described Agency's seven required
header fields as an exact six-line header.

## Approach

The user-facing correction now derives its numeric line count from
`HEADER_FIELDS`. Parser, formatter, and integration comments use
count-independent wording so a later field change cannot silently stale them.
A native Codex hook regression pins the resulting seven-line diagnostic and
its required continuation marker.

## Challenges encountered

The observed task still referenced a removed cached plugin bundle even though
the refreshed bundle was the only version on disk. The first test assertion
also incorrectly expected the diagnostic to end the reason, overlooking the
intentional continuation marker appended by the Codex adapter.

## Decisions and alternatives

Preserve historical six-line ADR titles and completed evidence records as
faithful history. Repair only the active runtime contract, maintained operator
guidance, and AR-199 current-state records.

## Verification

- Focused header, finalization, and native-hook coverage passes 66 tests.
- Ruff check and format pass all changed Python files.
- Documentation validation passes all 529 maintained Markdown files.
- `git diff --check` passes.

## Follow-ups

Run the named fast spine, merge and exact-install the revision, then prove the
nontrivial ordinary workforce path independently under AR-199.
