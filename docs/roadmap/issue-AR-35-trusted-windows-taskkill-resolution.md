---
title: "AR-35: Resolve Windows tree termination through a trusted system path"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [windows, process, security, delegation, portability]
related:
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-35
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/36"
depends_on: []
blocks: [AR-60]
---

# AR-35: Resolve Windows tree termination through a trusted system path

## Problem

Windows delegated-process cleanup launches `taskkill.exe` by a partial name.
Windows executable search can consult mutable locations, so cleanup can execute
the wrong binary even though other system helpers already use a trusted
System32 resolver.

## Current state

The child process remains owned by a Job Object where available and cleanup is
bounded, but the fallback helper crosses a PATH/CWD trust boundary. The shared
Windows resolver currently allowlists PowerShell and Task Scheduler only.

## Approach

Add `taskkill.exe` to the existing allowlisted Windows system resolver and use
its absolute, regular, non-reparse path for native tree termination. Preserve
data-only injected-runner seams and fall back to direct owned-process cleanup
when trusted resolution or launch fails.

## Dependencies

This extends the established trusted-system-command boundary and does not add a
new external dependency or architectural policy.

## Acceptance

- [x] Native taskkill execution never uses CWD or PATH lookup.
- [x] Missing or unsafe system binaries fail to direct owned-process cleanup.
- [x] Windows and POSIX process lifecycle regressions pass.
- [x] Security, exact-coverage, package, and tracker gates pass.
