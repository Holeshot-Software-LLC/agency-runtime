---
title: "Worklog detail: Retire Agency Windows Hello"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [architecture, security, windows, handoff, host-integrations]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/handoffs/issue-AR-196.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
supersedes: []
superseded_by: null
type: worklog
commit: 813651086f3d4ce8337cfe7956d435f8e88e86ac
short: 8136510
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
---

# Worklog detail: Retire Agency Windows Hello

## Purpose

Stop the unsuccessful dashboard-service verifier loop, preserve the last safe
code checkpoint, and record the owner's decision to remove Agency-owned Windows
Hello in favor of harness-native plugin trust.

## Approach

Removed the complete uncommitted AR-196 implementation draft, documented every
security and rollback discovery in one bounded recovery capsule, superseded the
two governing operator-presence decisions with ADR-0110, and opened AR-197 as
the implementation package. Routine plugin lifecycle is separated from the
optional dashboard service and model-facing mutation authority remains absent.

## Challenges encountered

The initial diagnosis treated dashboard repair as one missing native verifier.
Red-team review proved that activation spans task and process lifecycle,
launcher publication, owner and broker credential descriptors, Store startup
and retention writes, and rollback. A temporary foreground dashboard also ran
the existing retention-maintenance path before that side effect was understood;
it was stopped and its port was proven closed.

## Decisions and alternatives

[ADR-0110](../decisions/0110-remove-agency-owned-windows-hello.md) owns the
decision. Finishing more action-specific Windows Hello protocols was rejected
as duplicate security machinery around harness-native registration and trust.
Giving dashboard or MCP credentials persistent write authority was also
rejected.

## Verification

- Documentation validation passed for 503 Markdown files.
- Metadata, policy-availability, worklog-index, and diff checks passed before
  the substantive commit.
- The abandoned implementation left no tracked source or test delta; only the
  owner-untracked analysis draft and `uv.lock` remained.
- No exhaustive test, hosted workflow, tracker mutation, or release action ran.

## Follow-ups

- [AR-197](../roadmap/issue-AR-197-remove-agency-owned-windows-hello.md) removes
  the verifier and routes routine plugin lifecycle through harness-native trust.
- [AR-196](../roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md)
  remains fail-closed and is no longer a plugin-activation or demo dependency.
