---
title: "Worklog detail: Import Windows ctypes fixtures portably"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [testing, portability, windows, linux, ci]
related:
  - docs/roadmap/README.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: 664fcf18cdcc9c7b691827930f35a5bb807a8b1f
short: 664fcf1
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-103-import-windows-ctypes-fixtures-portably.md
---

# Worklog detail: Import Windows ctypes fixtures portably

## Purpose

Restore test collection on POSIX Python after PR #104 exposed an implicit
Windows-only import dependency in two ACL fixture modules.

## Approach

Import `wintypes` explicitly from `ctypes` and use that bound module for the
test-only `DWORD` structure fields. Production ACL code and the simulated API
behavior remain unchanged.

## Challenges encountered

The Windows suite passed because another platform import happened to populate
`ctypes.wintypes`; POSIX Python correctly made no such guarantee. The bundled
CI-log inspector also encountered a Windows code-page decoding error, so the
failed job logs were retrieved with its documented `gh run view` fallback.

## Decisions and alternatives

The fix stays in the fixtures. Adding a production import solely to satisfy test
collection would have hidden the test module's undeclared dependency and
coupled unrelated runtime imports.

## Verification

- Both focused Windows fixture modules: 36 passed with warnings as errors.
- WSL Ubuntu Python 3.12 resolved explicit `wintypes.DWORD` successfully.
- Ruff check, Ruff format, documentation validation, and diff checks passed.
- Hosted Ubuntu Python 3.11 through 3.14 remains the authoritative matrix gate.

## Follow-ups

Require every PR #104 Windows/Linux job to pass before closing AR-103.
