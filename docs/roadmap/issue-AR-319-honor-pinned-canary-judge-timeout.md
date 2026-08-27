---
title: "AR-319: Honor the pinned canary judge profile timeout"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [bug, canary, inference, timeout, codex]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/roadmap/issue-AR-318-bound-codex-activation-child-wait.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0183-honor-pinned-canary-judge-timeout.md
  - agency_runtime/core/canary_judge_provider.py
  - agency_runtime/core/native_child_staffing.py
  - tests/test_canary_child_judge_provider.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-319
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-319: Honor the pinned canary judge profile timeout

## Problem

The exact canary child-judge profile declares a 120,000-ms provider timeout,
but canary-only provider narrowing retains the legacy global 60-second judge
aggregate. The single pinned provider is therefore cut off before its own
bounded profile deadline, preventing an otherwise valid workforce envelope.

## Current state

- Exact repaired candidate `c6b7d92d` emits one `wait_agent` call with
  `timeout_ms=120000`; the child completes and the wait returns
  `timed_out=false`.
- The Store records `local-child-judge` as requested, 59 eligible cards, and
  `native_child_inference_unavailable` at 60,091 ms. The exact profile already
  has `timeout_ms=120000`; no model, alias, endpoint, or fallback is unknown.
- The child consequently receives only a 563-byte native identity record, not
  an `[AGENCY INFERENCE TEAM v6]` envelope. Strict projection correctly rejects
  the install rather than inferring delivery from the successful child result.
- Install `d61d1574...d23f`, Store `c16b99c1...1438`, and parent/child rollouts
  `e63a6865...1b8e`/`7a25e86f...c879` are retained mode 0600.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

When an activation canary resolves one explicit provider pin, build its
canary-only configuration with that provider's already validated timeout as the
aggregate judge budget. Preserve exactly one provider, no fallback, the global
configuration object, and the inference-profile 120-second maximum. Do not
change the selected alias, model, endpoint, thinking level, or outer canary
timeout.

## Dependencies

- AR-317 owns the authenticated LiteLLM-only alias topology and exact config.
- AR-318 owns the separate native child terminal wait.
- ADR-0174 requires one explicit canary-only judge without fallback.

## Acceptance

- [ ] A pinned canary provider's validated timeout becomes its aggregate judge
      budget without mutating ordinary configuration or fallback behavior.
- [ ] Focused warning-strict provider, staffing, and canary tests pass.
- [ ] A rebuilt fresh Codex production-container install persists one verified
      v6 delivery, consumption, accepted finalization, header, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
