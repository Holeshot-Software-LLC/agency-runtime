---
title: "AR-308: Bind activation canary delegation"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [canary, workforce, delegation, inference, validation]
related:
  - CHANGELOG.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - agency_runtime/core/selector/pipeline.py
  - agency_runtime/core/evals/decision_conformance.py
  - agency_runtime/core/workforce/inference.py
  - tests/test_activation_canary_contract.py
  - tests/test_workforce_inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-308
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297, AR-309]
---

# AR-308: Bind activation canary delegation

## Problem

The exact restricted AR-297 route accepted one inference-selected
`code-reviewer`, but the deterministic proposal builder always emitted
`delivery=load`. The activation canary's closed-world contract correctly
requires `delivery=delegate` so the native host, rather than the parent context,
executes the selected specialist. Projection therefore cleared the otherwise
valid team with `activation_canary_contract_invalid:delivery` before any child
or attestation could exist.

## Current state

- Diagnostic JSON SHA-256
  `b6dc0aa8398cc5600a06a2be532fc3ea89607f2caf1cf9bf640cc596bc7bc6e8`
  records session `ar297-restricted-route-228d0a4450c343f09c394931f91c74ff`
  and trace `530e8029-f455-40a2-b3aa-648cd14ae4a9`.
- Qwen planning, exact 4,096-dimensional additive embedding, Mistral
  reranking/recruitment, hard staffing verification, and the single reviewer
  selection all applied before the delivery-only rejection.
- Inference nominations intentionally own identities and ranks, not native host
  execution mode. The deterministic proposal default remains `load` for every
  ordinary route.
- Tracker creation is prohibited by the active AR-297 task.
- The exact rebuilt `1f32915d` canary now accepts `delivery=delegate`, loads
  `code-reviewer`, records one direct native delegation, and reaches the sole
  child conclusion. Its later Codex 0.149 host-artifact/header failure belongs
  to AR-309 rather than this delivery projection.
- The first named spine reached 859 passes with three skips but exited 1
  because the curated plan-subdivision mutation still anchored the former
  two-field canary options. Its source guard now preserves `delegate`, and a
  separate mutation proves changing delivery back to `load` is killed.

## Approach

Add one bounded optional delivery constraint to workforce planning. Validate it
before any provider call, then bind only that execution field after the raw
inference-owned proposal is recovered and before deterministic verification and
strict criticism. The exact activation-canary path supplies `delegate`; all
ordinary callers omit the constraint and keep `load`.

Keep cached recruiter proposals unmodified so an activation-canary lookup
cannot poison a later ordinary route. Do not change model routes, ranking,
selection, staffing thresholds, strict assurance, child-judge policy, or the
closed-world activation projection.

## Dependencies

- ADR-0118 retains inference ownership of specialist selection and ranking.
- ADR-0173 requires a normal no-bypass native child lifecycle before managed
  production-container activation may attest.
- AR-297 supplies the exact configuration and restricted capability receipt.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] The exact restricted diagnostic isolates delivery as the sole activation
      contract violation after an accepted inference-owned selection.
- [x] The activation-canary planner requests one `delegate` delivery contract.
- [x] Deterministic verification and the strict critic receive that exact
      delivery while selection and ranking remain unchanged.
- [x] Invalid delivery constraints fail before provider invocation.
- [x] Cached recruiter output remains `load` for a later ordinary route.
- [x] Decision conformance independently mutates `delegate` back to `load`, and
      the focused activation contract kills that mutation.
- [x] Focused warning-strict tests pass 196 with one expected skip; changed-file
      Ruff, formatting, and diff checks pass.
- [ ] A rebuilt exact Codex production-container transaction completes the
      no-bypass managed canary and persists a current attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
