---
title: "AR-181: Bound all-host smoke launcher preparation"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [testing, performance, packaging, host-integrations]
related:
  - agency_runtime/core/smoke.py
  - tests/test_smoke_coverage_complete.py
  - tests/test_smoke_isolation.py
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-181
priority: p1
tracker_url: null
depends_on: []
blocks:
  - AR-160
---

# AR-181: Bound all-host smoke launcher preparation

## Problem

`agency smoke --all --json` prepares the same immutable private package runtime
once per generated host. On the fresh Windows candidate this repeated an
821-file bounded read for every host and exceeded a 122-second outer ceiling,
even though every host consumes the same launcher identity.

## Current state

The packaged distribution smoke itself passes in 3.5 seconds. The separate
all-host smoke was the slow step: a diagnostic stack captured every host inside
`_collect_runtime_files()` through `_prepare_adapter_launcher_paths()`. No live
inference or native registration was involved. Current source prepares one
attested launcher closure lazily, binds that immutable pair around each host
check, and completes all five generated-host checks in 43.9 seconds.

Tracker creation remains pending explicit outward-write authorization.

## Approach

Prepare one launcher only when a smoke invocation has multiple hosts. Reuse the
already attested private interpreter/bootstrap pair through the existing scoped
launcher binding while retaining every per-plugin manifest, hook, syntax,
idempotency, toggle, and subprocess validation. Cache a preparation failure only
inside that smoke invocation and report it through each typed host result.

## Dependencies

AR-156 owns the bounded verification strategy. AR-160 owns exact artifact and
fresh-install evidence.

## Acceptance

- A multi-host smoke prepares the private launcher exactly once.
- Every selected host still receives its own isolated temporary home and full
  generated-plugin contract check.
- Launcher preparation failure remains a typed smoke failure and cannot become
  a skip or success.
- `agency smoke --all --json` completes successfully under a two-minute local
  ceiling on the measured Windows machine.
- A fresh exact wheel repeats the packaged smoke and all-host smoke without
  native registration, live inference, or operator-presence prompts.

## Implementation evidence

The focused isolation and smoke suites pass 34 tests. Ruff, formatting, and
diff checks pass. A real source invocation passes eight checks with zero failures
or skips in 43.9 seconds, versus the pre-fix 122.4-second outer timeout.
