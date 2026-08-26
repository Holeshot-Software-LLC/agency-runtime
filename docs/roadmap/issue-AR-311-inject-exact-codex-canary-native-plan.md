---
title: "AR-311: Inject the exact Codex canary native plan"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, delegation, hooks, production-container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/adapters/hooks.py
  - tests/test_activation_canary_contract.py
  - tests/test_canary_activation_snapshot.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-311
priority: p0
tracker_url: null
depends_on: [AR-309, AR-310]
blocks: [AR-297]
---

# AR-311: Inject the exact Codex canary native plan

## Problem

The post-AR-310 managed Codex canary persists the exact accepted
`code-reviewer` delegate route, but its parent context contains generic
instructions to follow an `[AGENCY DELEGATION PLAN]` without containing a
concrete plan row. Codex therefore derives `task_name=code-reviewer` from the
specialist slug. Codex requires lowercase letters, digits, and underscores, so
the only spawn fails before a child exists and the AR-309 delivery boundary
cannot run.

## Current state

- Exact candidate `c60678ef352e43db253b2d3d6e0fb162f80bfbf7` has wheel
  `3c8eb01b...09c4e`, sdist `8b8db82c...39131`, Codex image
  `49493058...c9a5c`, and fresh container `30b2b90c...be88`. Its mode-0600
  absence receipt hashes to `a5c70707...28b0d`.
- The no-bypass production install exits 1 with empty stderr and mode-0600 JSON
  SHA-256 `a58dae29...4ad7`. Managed policy is current and
  `trust_bypass_used=false`.
- Session `01a03fe6-c434-7432-a7ef-8d5535109e8c`, trace
  `01a03fe6-c43f-7790-b15d-582199c78b2b`, and query
  `eab71210...97d80` prove one accepted `code-reviewer` route, one exact fixed
  delegate unit, and one specialist load. There is no delegation, worker run,
  native route, native delivery, or activation receipt.
- Parent rollout `fe8aedb9...2d6` is the canonical host artifact. Its sole
  `spawn_agent` call uses `task_name=code-reviewer`; the host returns
  `agent_name must use only lowercase letters, digits, and underscores`.
- Finalization `d7160d7b-7e22-40f4-b13d-4bbba01be04c` is
  `response_invalid` with missing `evidence_verification`; no attestation
  exists. Tracker creation is prohibited by the active AR-297 task.

## Approach

Render one canonical canary-only plan row after preflight and append it to the
Codex `UserPromptSubmit` context only when the restricted environment, exact
Store-backed live parent, matching session and trace, accepted inference-owned
route, sole `code-reviewer`, fixed unit, and `delivery=delegate` all agree. The
row pins `native_task_name=code_reviewer`, the fixed goal, work-unit ID, empty
dependencies, and exactly-once execution.

Do not add an ordinary delegation nudge or infer a specialist. Any absent,
forged, mismatched, oversized, or non-canary input leaves the plan absent and
the proof fails closed. ADR-0179 already requires this exact canary row, so this
is a bounded conformance repair rather than a new durable decision.

## Dependencies

- AR-309 supplies the exact 0.149 child-artifact and receipt boundary reached
  only after a valid native spawn.
- AR-310 supplies the existing-Store restriction required to resolve the live
  parent route.
- ADR-0173 requires a normal managed-policy invocation with no trust bypass.
- ADR-0179 permits only the fixed Store-backed canary delivery exception.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] A fresh exact no-bypass container reproduces the missing-row failure with
      exact exit, hashes, Store IDs, and canonical parent artifact.
- [x] The hook renders exactly one canonical `code_reviewer` row only for the
      Store-proven restricted canary parent.
- [x] Ordinary and mismatched routes receive no plan; exact goal, specialist,
      work-unit ID, and native task label are golden-pinned.
- [x] Focused warning-strict Codex, hook, Store, installer, and security tests
      pass (545 tests).
- [ ] A rebuilt fresh transaction spawns `code_reviewer` exactly once and
      either persists the full attestation or reports the next honest blocker.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
