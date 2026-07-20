---
title: "AR-111: Honor global Agency mode in isolated host canaries"
status: in_progress
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

A real Codex 0.144.3 control reproduced the defect: the global switch committed
disabled and was restored in a guaranteed cleanup block, but the isolated
invocation still produced a valid Agency header, one routing event, and two
finalizations. No native-only result is claimed from that run.

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

- [ ] The isolated profile materializes the authoritative current master state.
- [ ] Agency mode refuses execution while the authoritative master is disabled.
- [ ] Native-only mode refuses execution while the authoritative master is enabled.
- [ ] Native-only success requires a completed nonempty response, registered plugin, no Agency header, and zero new Agency evidence.
- [ ] Native-only success does not create an Agency canary attestation.
- [ ] Control read/materialization errors and state drift fail closed.
- [ ] Focused line/branch, full suite, hosted matrix, and exact installed Codex A/B canaries pass.
- [ ] Documentation, worklog, and tracker mappings remain synchronized.
