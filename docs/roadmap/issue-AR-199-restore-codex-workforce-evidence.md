---
title: "AR-199: Restore Codex workforce selection and evidence"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [codex, routing, workforce, receipts, resident-managers, regression]
related:
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/roadmap/handoffs/issue-AR-199.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-199
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-199: Restore Codex workforce selection and evidence

## Problem

The exact merged default installation loads Agency's Codex plugin, but the
first trusted production task exposed a broken end-to-end workforce contract.
The resident-manager binding is present while model-authored headers can report
`loaded: none`; nontrivial inferred work can abstain with no specialist; model
provider attempts are not persisted; contractor hiring is unavailable; and the
activation canary rejects its own native child goal.

## Current state

Exact installed revision `6fc3173901af94d03f7d61a350a14892083e3735`
successfully registered Codex and ZCode and started the dashboard. A fresh
trusted Codex task received the resident-manager kernel, proving plugin load.
The current local evidence store contains 272 active workers, 97 runs, 85
routing decisions, zero model receipts, and one specialist-load row.

The observed nontrivial turn was correctly classified with
`selection_required=true`, and two configured provider calls returned applied
structured responses. It produced four verified work units but no unit-agent
plan. The content-free receipt reports 219 evaluated workers, zero eligible,
capability/platform exclusions, and `hiring_store_unavailable`. Source review
shows that preflight deliberately calls routing with `store=None`; this
preserves ready-CAS atomicity but makes receipt persistence and same-task hiring
unavailable. Passing the live store directly would reintroduce partial writes
and is not an acceptable repair.

The normal-profile activation verifier separately reached its live canary, but
the installed `PreToolUse` hook rejected the sole `spawn_agent` call because
the emitted task did not exactly match the persisted work-unit goal. The result
was `codex_collaboration_projection_unavailable`, not a hook-trust failure.

## Approach

Preserve the atomic preflight boundary. Project bounded provider receipts and
governed workforce changes as pending evidence, validate them before the ready
CAS, and commit the allowed evidence with the turn rather than giving the
planner an unscoped live Store. Keep the two resident managers in completion
evidence independently of specialist selection. Repair the activation canary's
parent instruction or goal projection so its one native child uses the exact
persisted goal without weakening `PreToolUse` validation.

## Dependencies

AR-119 owns inference-first planning, staffing, and governed hiring. AR-195 and
ADR-0077 own the exact Codex activation canary. ADR-0003 and ADR-0065 govern
model truth and resident-manager visibility.

## Acceptance

- [ ] Every enabled Codex parent turn with a valid resident binding reports
  `agents-orchestrator, chief-of-staff` as loaded, even when no specialist is
  selected.
- [ ] Configured workforce provider attempts are committed as current-turn
  model receipts without leaving evidence behind after a failed preflight.
- [ ] Same-task gap hiring can use the governed Store without bypassing the
  ready-CAS or creating partial workforce state.
- [ ] A nontrivial four-unit request against the active workforce produces a
  verified unit-agent plan or a complete truthful gap/hiring outcome; it does
  not silently collapse to a generic no-match result.
- [ ] The Codex activation canary launches exactly one goal-bound specialist,
  waits exactly once, and persists a complete attestation.
- [ ] Focused tests cover header reconciliation, atomic receipt persistence,
  hiring availability, and exact canary goal binding.
- [ ] The named fast production spine and routing evaluation pass.
- [ ] A fresh exact-installed Codex task visibly reports both resident managers,
  at least one accepted specialist for an explicit bounded work unit, and an
  authoritative provider/model receipt.
