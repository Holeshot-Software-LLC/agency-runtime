---
title: "AR-330: Support Codex 0.150 collaboration rollouts"
status: in_progress
category: roadmap
created: 2026-08-28
updated: 2026-08-28
tags: [bug, codex, activation, rollout, compatibility, linux]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/adapters/hooks.py
  - tests/test_codex_activation_canary.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-330
priority: p0
tracker_url: null
depends_on: [AR-313, AR-314]
blocks: [AR-297]
---

# AR-330: Support Codex 0.150 collaboration rollouts

## Problem

Codex 0.150.1 adds an explicit `agent_type` to `spawn_agent`, records the role
and a generated nickname in child lineage, and emits a terminal `completed`
`SubAgentActivity`. Agency's exact 0.149 projection rejects those additional
host-authored fields and therefore cannot verify an otherwise valid current
Codex install. Pinning or downgrading Codex would hide the compatibility defect.

## Current state

- The retained 0.150.1 parent and child rollouts prove one `Code Reviewer`
  spawn, one bounded terminal wait, one started activity, and one completed
  activity with exact child/path agreement.
- The pre-repair hook admits only the 0.149 implicit `default` role, so the
  retained negative run correctly contains no Agency staffing delivery.
- This host uses umask `0002`; AR-313's integrity guard needs to recognize the
  owner-exclusive user-private group without admitting a second account.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Request the exact `Code Reviewer` native role, admit both the legacy implicit
and new explicit canary shapes, and bind new lineage/activity fields to the
same call, child UUID, path, role, and terminal lifecycle. Extend foreign
Codex-artifact integrity only when POSIX account data proves the artifact group
is the owner's exclusive user-private group. Keep links, foreign ownership,
other-writability, shared groups, cardinality drift, and content mutation
fail-closed.

## Dependencies

- AR-313 owns foreign Codex artifact integrity.
- AR-314 owns the canary child-role binding.
- ADR-0156 and ADR-0179 require exact host-authored child delivery evidence.

## Acceptance

- [x] Real 0.150.1 rollout copies reproduce explicit role, nickname, and
      terminal-activity variance without retaining prompt or secret content.
- [x] Focused tests cover both 0.149 and 0.150 exact canary projections.
- [x] Group-writable artifacts are accepted only for a proven exclusive
      user-private group; shared groups and other-writable paths remain refused.
- [ ] A rebuilt exact candidate staffs and verifies a live Codex 0.150.1 child
      without a bypass or version pin.
- [ ] Ordinary Codex product execution loads Agency unattended and its Store,
      prompt, response, and host-artifact correlations pass.
- [ ] Every named repository gate passes for the exact candidate.
- [ ] A same-repository tracker issue is created after explicit authorization.
