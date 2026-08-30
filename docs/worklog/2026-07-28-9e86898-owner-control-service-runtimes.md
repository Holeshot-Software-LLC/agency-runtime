---
title: "Worklog detail: Preserve Windows owner control and service runtimes"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [windows, security, controls, dashboard, python]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/decisions/0058-broker-restricted-windows-host-controls.md
  - docs/decisions/0060-restricted-windows-cli-read-and-fail-safe.md
supersedes: []
superseded_by: null
type: worklog
commit: 9e86898
short: 9e86898
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
---

# Worklog detail: Preserve Windows owner control and service runtimes

## Purpose

Restore authoritative master-control reads for normal UAC-filtered Windows
owners and make an upgraded CLI inspect an owned dashboard runtime created by a
different Python interpreter without weakening execution compatibility.

## Approach

The canonical master reader now tries the strict owner-private path first. It
enters the reduced Windows reader only after a strict security refusal and a
positive canonical restricted-token check. Explicit uncached reads bypass the
reduced cache, and the authenticated dashboard master endpoint reads the tiny
control document uncached.

Private-runtime inspection validates the recorded cache tag as part of the
immutable manifest but no longer equates it with the inspecting CLI's tag.
Preparation and execution remain current-tag-only. Before a dashboard worker
can be prepared, the selected trusted Python executable is identity-snapshotted,
probed with fixed shell-free isolated arguments, compared byte-for-byte with
the current validated tag, and revalidated; the resulting Python and bootstrap
identities are then revalidated together.

## Challenges encountered

The live Codex activation attempt stopped safely before model use because the
normal UAC-filtered owner process was routed into the restricted reader and a
stale dashboard descriptor could not broker the real generation-28 master
state. Cross-interpreter service status then exposed a second defect: a CPython
3.10 CLI rejected the valid CPython 3.13 immutable service manifest. One broad
local test command timed out and left a Windows child briefly alive; it was
discarded as evidence, the exact orphan was terminated, and the suites were
rerun once in short sequential groups.

## Decisions and alternatives

The change does not weaken ACL validation, the reduced reader's negative
mutation proof, or dashboard authentication. Treating every
`TokenHasRestrictions` result as a sandbox remained unsuitable because normal
UAC filtering sets it. Reusing a foreign runtime for execution was also
rejected: read-only inspection may be interpreter-neutral, but construction and
execution require the exact current cache tag and a probe of the selected
Python. The unavailable generic operator-presence path was not bypassed to
repair the stale scheduled service.

## Verification

- Master-control module: 108 passed, 4 skipped.
- Changed dashboard master routes: 4 passed.
- Launcher and service-core focus: 78 passed.
- Full dashboard-service module: 77 passed.
- Canary modes and activation verification: 49 passed.
- Named fast Python production spine: 536 passed, 5 skipped in 73.51 seconds.
- Dashboard UI: 109 passed.
- Routing, policy, delegation, performance, retrieval-scale, and CLI-startup
  evaluation: every gate passed.
- Ruff lint/format: 604 files passed; documentation validation: 495 files.
- Two independent final reviews found no remaining scoped Critical, High, or
  Medium issue.

## Follow-ups

- [AR-193](../roadmap/issue-AR-193-preserve-authoritative-windows-master-reads.md)
  still needs exact installed-package and bounded live-canary evidence.
- [AR-194](../roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md)
  still needs an attended owner-side replacement of the stale dashboard task
  and runtime; generic dashboard-service mutation authority remains unavailable.
