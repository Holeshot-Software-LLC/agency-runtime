---
title: Make hosted process-security fixtures race-free and platform-honest
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [testing, portability, processes, security, ci]
related:
  - docs/roadmap/issue-AR-109-hosted-process-security-test-fidelity.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 984302557b9cafc3f92c827370219a376b834e51
short: 9843025
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111
related_issues:
  - docs/roadmap/issue-AR-109-hosted-process-security-test-fidelity.md
---

# Worklog detail: Make hosted process-security fixtures race-free and platform-honest

## Purpose

Fix the two test-fidelity defects exposed by PR #111's hosted Linux Python 3.13
and 3.14 cells without weakening production executable or containment checks.

## Approach

The Windows suffix simulation now supplies an absolute NT lexical spelling and
a frozen regular-file identity, so POSIX runs reach the intended native-suffix
guard. A shared readiness predicate now parses each PID file as one complete
positive integer before any affected lifecycle test reads or opens that PID.

## Challenges encountered

File creation is observable before a writer completes its payload. Python 3.14
made that test race visible when a descendant PID file existed with zero bytes.
Likewise, passing a real POSIX temporary path with `platform_name="nt"` tested an
invalid simulation rather than the Windows suffix policy.

## Decisions and alternatives

Production code remains unchanged and fail-closed. The rejected alternatives
were accepting cross-platform relative paths, weakening the suffix check,
sleeping for an arbitrary delay, or retrying an unvalidated PID after failure.

## Verification

- Windows affected files: 54 passed, 15 expected platform skips.
- Native WSL exact hosted reproductions: 3/3 passed.
- Native WSL affected files: 97 passed, 3 expected platform skips.
- Ruff, formatting, documentation, tracker mapping, and whitespace gates passed.

## Follow-ups

Require the complete hosted matrix to pass before marking
[AR-109](../roadmap/issue-AR-109-hosted-process-security-test-fidelity.md) done
or merging PR #111.
