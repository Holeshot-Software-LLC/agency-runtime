---
title: "Accept null OpenClaw control errors"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [openclaw, bridge, control, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/adapters/openclaw/node_bridge.py
  - tests/test_host_boundary_hardening.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-268
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-268: Accept null OpenClaw control errors

## Problem

The OpenClaw bridge returned a valid enabled-status object containing
`error: null`, then exited with status 2 because its process boundary treated
the presence of the key as failure. OpenClaw consequently classified Agency as
unavailable and blocked every Telegram or Slack turn before a reply was queued.

## Current state

The exact live failure is preserved from the 2026-08-21 Linux installation:
the bridge emitted `ok: true`, `runtime_enabled: true`, and `error: null`, while
the process receipt was exit 2. The gateway log then recorded
`before_agent_run hook blocked by agency-preflight` and a visible Telegram turn
with no queued reply payload.

A focused regression reproduces the null-error receipt and fails before the
repair. The bounded implementation now exits nonzero only for a truthy error;
existing real-error tests remain green. Reinstallation and fresh Telegram proof
remain pending.

## Approach

1. Preserve a unit test for the exact success payload with `error: null`.
2. Change only the bridge exit predicate; do not alter control, preflight,
   finalization, evidence, or child-delivery policy.
3. Reinstall OpenClaw from the repaired checkout after baseline Telegram is
   proven and use a completely fresh session.

## Dependencies

- AR-119 host activation and LiteLLM routing proof.
- Audited OpenClaw `2026.7.x` host state.
- Agency harness profile `linux-task-agency-router` in Agency configuration.

## Acceptance

- [x] A pre-fix regression proves `error: null` incorrectly returned exit 2.
