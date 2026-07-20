---
title: "AR-111: Honor global Agency mode in isolated host canaries"
status: done
category: roadmap
created: 2026-07-20
updated: 2026-07-20
tags: [canary, runtime-control, codex, testing, observability]
related:
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-79-installed-isolated-header-proof.md
  - docs/roadmap/issue-AR-88-compare-agency-native-outcomes.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-111
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/115
depends_on: []
blocks: []
---

# AR-111: Honor global Agency mode in isolated host canaries

## Problem

`agency off --global` leaves native plugins registered so operators can compare
fresh sessions with and without Agency. The isolated host canary replaces the
user home but does not materialize the authoritative master-control state into
that profile. A canary started while Agency is globally off therefore defaults
back to enabled, emits routing/finalization evidence, and falsely exercises the
Agency-on path.

## Current state

The original Codex 0.144.3 control reproduced the defect: the global switch
committed disabled and was restored in a guaranteed cleanup block, but the
isolated invocation still produced a valid Agency header, one routing event,
and two finalizations. That observation is retained as failure evidence, not a
native-only result.

The exact installed post-fix candidate then passed both guarded modes with
managed bundle digest
`ebff397c0ce2d6a6c703cea0151eb71f5455038a0f94431b0b2d995148c80bbe`.
Agency mode at global generation 16 produced a valid six-line header, one
routing event, one run, two finalizations, and persisted trace
`019f8112-0f85-76a3-87c3-c56c2ecf8943`. Native-only mode at generation 17
completed with the plugin registered, no valid Agency header, zero rows in all
six evidence categories, and no attestation write. Guaranteed cleanup restored
Agency-on at generation 18.

The hosted candidate matrix passed full Ubuntu Python 3.10 through 3.14 and
Windows Python 3.10/3.14 suites, exact 100% line/branch coverage, routing and
delegation performance, dashboard UI, artifact build/smoke/byte parity on both
operating systems, dependency review, and static analysis.

## Approach

Bind each isolated canary to one authoritative master-control snapshot and
materialize that state in its owner-private temporary home before the host
starts. Add an explicit `agency` or `native-only` canary mode with a distinct
confirmation phrase. Agency mode requires correlated header/evidence and may
persist an Agency attestation. Native-only mode requires a completed nonempty
host response, unchanged isolated plugin registration, no Agency header, and
zero new Agency evidence; it never writes an Agency-loading attestation.
Generated Codex and Claude hooks bind the installer-owned canonical control path
explicitly. Restricted Windows hooks may recover that exact master document only
through the authenticated local dashboard; every invalid or unavailable path
fails enabled.

## Dependencies

AR-57/ADR-0053 define the global fail-enabled control. AR-79 and ADR-0036 define
isolated canary evidence. AR-88 consumes honest paired mode observations.

## Acceptance

- [x] The isolated profile materializes the authoritative current master state.
- [x] Agency mode refuses execution while the authoritative master is disabled.
- [x] Native-only mode refuses execution while the authoritative master is enabled.
- [x] Native-only success requires a completed nonempty response, registered plugin, no Agency header, and zero new Agency evidence.
- [x] Native-only success does not create an Agency canary attestation.
- [x] Control read/materialization errors and state drift fail closed.
- [x] Focused line/branch, full suite, hosted matrix, and exact installed Codex A/B canaries pass.
- [x] Documentation, worklog, and tracker mappings remain synchronized.
