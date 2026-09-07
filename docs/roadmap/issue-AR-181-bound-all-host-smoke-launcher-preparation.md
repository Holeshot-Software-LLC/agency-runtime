---
title: "AR-181: Bound all-host smoke launcher preparation"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [testing, performance, packaging, host-integrations]
related:
  - docs/decisions/0026-explicit-test-home-boundaries.md
  - docs/roadmap/handoffs/issue-AR-181.md
  - docs/roadmap/acceptance/evidence/AR-181-smoke-reconciliation-20260907.md
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
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

Implementation commit `c625bc76707e169f4c4100fb6dc1247bbddb77c7` already added
one invocation-local, lazy launcher preparation for multi-host smoke. The
historical Windows measurement was 43.9 seconds after a 122.4-second outer
timeout before repair; it is not a fresh Windows qualification.

The September 7 read-only investigation found that source and tests deliberately
share one explicitly allocated private temporary home and Store across the
selected generated hosts. Each host has a distinct bundle path inside that
boundary. The original implementation's parent already used one home; the
literal separate-home-per-host acceptance bullet below was contradictory when
written, not a later isolation regression. ADR-0026 requires an explicit
`home_dir` boundary away from the operator profile, not a different home for
each host. This reconciliation explicitly corrects criterion 2 to that existing
contract; the original wording is preserved in the evidence receipt. It does
not introduce a new isolation architecture or manufacture a verifier verdict.

The [portable evidence receipt](acceptance/evidence/AR-181-smoke-reconciliation-20260907.md)
records 37 focused tests passing with two Windows-labelled cases deselected,
and the actual installed Linux `agency smoke --all --json` passing all eight
checks in 4.25 seconds. It also links AR-407's separate exact fresh-wheel
packaged smoke and five-host aggregate smoke in 5.09 seconds. Those are distinct
runs and neither establishes native harness activation or Windows timing.

The issue remains `in_progress`: preserve the explicit Windows-only under-two-
minute hold. Criterion 2 is explicitly reconciled below against ADR-0026.
No acceptance verdict or completion claim is
made here. Tracker URL is still null; publication owns tracker reconciliation.

## Approach

Prepare one launcher only when a smoke invocation has multiple hosts. Reuse the
already attested private interpreter/bootstrap pair through the existing scoped
launcher binding while retaining every per-plugin manifest, hook, syntax,
idempotency, toggle, and subprocess validation. Cache a preparation failure only
inside that smoke invocation and report it through each typed host result.

## Dependencies

AR-156 owns the bounded verification strategy. AR-160 owns exact artifact and
fresh-install evidence. ADR-0026 governs explicit generated-host home isolation;
AR-291 prevents alternate-home generation from publishing real runtime
pointers. AR-407 owns the separately built exact wheel and fresh installed
smoke receipt reused here, not a new AR-181 execution.

## Acceptance

- A multi-host smoke prepares the private launcher exactly once.
- Every selected host receives its full generated-plugin contract check within
  the invocation's explicitly supplied private temporary home, isolated from
  the operator home, with a distinct host-specific bundle path.
- Launcher preparation failure remains a typed smoke failure and cannot become
  a skip or success.
- `agency smoke --all --json` completes successfully under a two-minute local
  ceiling on the measured Windows machine.
- A fresh exact wheel repeats the packaged smoke and all-host smoke without
  native registration, live inference, or operator-presence prompts.

## Implementation evidence

### Historical implementation evidence

The original record reported packaged distribution smoke in 3.5 seconds and
diagnostic stacks showing repeated `_collect_runtime_files()` calls through
`_prepare_adapter_launcher_paths()` during all-host smoke. No live inference or
native registration was involved in those observations.

The focused isolation and smoke suites pass 34 tests. Ruff, formatting, and
diff checks pass. A real source invocation passes eight checks with zero failures
or skips in 43.9 seconds, versus the pre-fix 122.4-second outer timeout.

### September 7 reconciliation

The new receipt separates current source contracts, historical implementation,
fresh focused Linux tests, the existing installed CLI observation, and AR-407's
exact fresh wheel. A bounded preparation-failure diagnostic produced one
preparation attempt, zero generated-plugin calls, three typed host failures and
zero skips. It was an in-memory diagnostic, not a newly committed regression.

No native Windows execution, native host registration, live model inference,
operator-presence prompt, exhaustive suite, coverage shard, or compatibility
matrix was run for this reconciliation. No operator-profile before/after hash
audit was performed, so none is claimed. The
[active capsule](handoffs/issue-AR-181.md) records the remaining bounded work.
