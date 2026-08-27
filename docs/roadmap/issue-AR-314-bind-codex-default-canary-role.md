---
title: "AR-314: Bind the Codex 0.149 default canary child role"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, hooks, native-child, production-container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/canary_backends.py
  - tests/test_codex_activation_verification.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-314
priority: p0
tracker_url: null
depends_on: [AR-309, AR-311]
blocks: [AR-297, AR-315, AR-322]
---

# AR-314: Bind the Codex 0.149 default canary child role

## Problem

AR-311 correctly gives Codex the exact native `task_name=code_reviewer`, and a
fresh transaction creates that child. Codex MultiAgentV2 stores `task_name` as
the child `agent_path`; because the exact canary spawn omits the optional
`agent_type`, Codex 0.149.1 emits `agent_type=default` at `SubagentStart`.
Agency incorrectly required `agent_type=code_reviewer`, so it returned only the
identity context and never delivered the Store-proven v6 workforce card.

## Current state

- Exact candidate `49bf1190` reaches the accepted parent route and completes
  child `01a04005-8353-7f42-9020-3453eed3b5b0` with exit 0. The child receives
  only the 563-byte identity context at SHA-256 `221ada...`; no v6 team marker,
  native child staffing decision, delivery receipt, or activation grant exists.
- Official Codex tag `rust-v0.149.1` defines `agent_type` as required hook
  output, maps an omitted role to built-in `default`, and keeps `task_name` in
  the agent path. This is host schema, not staffing authority.
- The bounded repair pins the restricted canary hook to exactly `default` and
  independently requires the canonical child rollout to report no explicit
  `agent_role`. The accepted Store route, fixed work unit, parent/child UUIDs,
  and delivery receipt still select and prove `code-reviewer`.
- Ordinary, explicit-role, mismatched, and opaque spawns remain unstaffed.
  Tracker creation is prohibited by the active AR-297 task.
- Later exact evidence confirms `SubagentStart` supplies the child session UUID,
  not the parent session; AR-322 owns that independent correlation repair.

## Approach

Name the exact Codex 0.149 built-in role in the version-shaped activation
contract. Treat it only as one lifecycle-schema discriminator; never infer a
specialist or work unit from it. Require the already-persisted accepted canary
route and all ADR-0179 bindings before delivery, and reject a child rollout
that claims any explicit role.

## Dependencies

- AR-311 supplies the exact `code_reviewer` task path and fixed plan.
- AR-309 and ADR-0179 supply the Store/UUID/artifact/receipt authority chain.
- ADR-0173 requires a no-bypass normal managed-policy invocation.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] The exact live child reproduces `task_name=code_reviewer` with host role
      `default` and identity-only context.
- [x] The restricted hook admits exactly the built-in default lifecycle role
      while taking selection only from the proven Store route.
- [x] The child rollout must preserve an omitted explicit role and the exact
      `agent_path=code_reviewer`; drift fails closed.
- [x] Ordinary/mismatched spawns remain unstaffed and the parent route survives
      an opaque PreToolUse event.
- [x] Focused warning-strict activation, provenance, delivery, hook, and
      storage tests pass (586 plus two artifact-parent regressions).
- [ ] A rebuilt fresh no-bypass Codex transaction writes one complete v6 child
      artifact, consumes its receipt, and persists the activation attestation
      or exposes a later honest blocker.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
