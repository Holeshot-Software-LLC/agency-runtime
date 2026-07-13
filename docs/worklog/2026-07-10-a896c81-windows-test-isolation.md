---
title: "Worklog: isolate generated-plugin tests from the user profile"
status: active
category: worklog
created: 2026-07-10
updated: 2026-07-13
tags: [testing, windows, portability, safety]
related:
  - docs/decisions/0026-explicit-test-home-boundaries.md
supersedes: []
superseded_by: null
type: worklog
commit: a896c817739757062071bb172156b60b9afb686a
short: a896c81
date: 2026-07-10
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
---

# Worklog: isolate generated-plugin tests from the user profile

## Purpose

Fix AR-09 so generated-host tests and smoke checks cannot write into the
operator's real profile and the complete suite provides a trustworthy signal on
both Windows and Linux.

## Approach

- Added an explicit `home_dir` boundary to host detection, installation, and
  toggling, with containment validation that rejects escaping paths.
- Passed temporary homes directly from tests and smoke checks instead of
  relying on platform-specific environment expansion.
- Wrote every generated plugin and manifest as UTF-8.
- Replaced POSIX string and shell-built-in assumptions with platform-neutral
  `Path` and executable fixtures.
- Made OpenClaw smoke checks validate manifests and required source structure
  on every platform, using `node --check` when Node is runnable and reporting a
  visible skip otherwise.

## Challenges encountered

- Windows home expansion ignored the test's `HOME` override and exposed the
  operator's real plugin directory.
- A Linux run found a Windows-interoperability `node` path that was discoverable
  but not executable. Static package validation was kept mandatory while the
  optional syntax check became capability-aware.
- Previously generated real-profile plugin files could not be safely removed
  without knowing whether they replaced an intentional installation, so they
  were preserved and monitored by hash and timestamp.

## Decisions and alternatives

- [ADR-0026](../decisions/0026-explicit-test-home-boundaries.md) records the
  explicit-home safety boundary and capability-aware OpenClaw validation.
- Adding more platform environment variables was rejected because it leaves the
  install destination implicit.
- Disabling host smoke coverage was rejected because generated artifacts remain
  a public installer contract.

## Verification

- Windows: 185 tests passed.
- Ubuntu/WSL: 185 tests passed.
- The explicit `~/../outside` regression is rejected before any write.
- Real-profile Codex plugin hashes, lengths, and timestamps were identical
  before and after the final Windows suite.
- Documentation metadata, links, decision registry, and roadmap dependency
  validation passed for 42 Markdown files before this detail record.

## Follow-ups

- Close tracker issue AR-09 after outward-facing closure is approved.
- Leave the old generated real-profile Codex plugin files untouched until the
  operator explicitly chooses whether to retain or remove them.
