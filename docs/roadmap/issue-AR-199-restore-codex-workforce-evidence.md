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
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
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

The first merged repair reached the trusted live canary and selected
`code-reviewer`, but replacing Codex's opaque encrypted spawn message produced
a mixed plaintext/encrypted child envelope. The child received the exact
specialist prompt and then failed to decrypt the retained encrypted content;
the verifier also omitted `agent_message` input while projecting delivery.

## Approach

The implementation preserves the atomic preflight boundary while giving
workforce routing governed Store reads. It projects bounded provider receipts
and validated workforce changes as pending evidence, hydrates pending
specialists through a nonpersistent view, and commits the allowed evidence only
inside the winning ready CAS. It also recognizes Codex's opaque persisted spawn
message only for the package-owned canary goal after exact parent, task-label,
and assignment correlation; ordinary child goals retain exact equality.

The follow-up preserves Codex's opaque tool input unchanged. It stages the
native-hook grant at `PreToolUse`, retrieves one unambiguous prompt only after
the exact child lifecycle is persisted, injects that prompt through
`SubagentStart`, and consumes the grant at `PostToolUse` using exact tool-call
and lifecycle evidence. Rollout parsing now accepts the observed
`agent_message` delivery shape and rejects task-complete records with a decrypt
error or no final child message. Live proof showed that the exact delivery must
also be the complete `SubagentStart` context: prefix or suffix guidance changes
the strict original-task or prompt-body hash boundary.

## Dependencies

AR-119 owns inference-first planning, staffing, and governed hiring. AR-195 and
ADR-0077 own the exact Codex activation canary. ADR-0003 and ADR-0065 govern
model truth and resident-manager visibility.

## Acceptance

- [x] Every enabled Codex parent turn with a valid resident binding reports
  `agents-orchestrator, chief-of-staff` as loaded, even when no specialist is
  selected.
- [x] Configured workforce provider attempts are committed as current-turn
  model receipts without leaving evidence behind after a failed preflight.
- [x] Same-task gap hiring can use the governed Store without bypassing the
  ready-CAS or creating partial workforce state.
- [ ] A nontrivial four-unit request against the active workforce produces a
  verified unit-agent plan or a complete truthful gap/hiring outcome; it does
  not silently collapse to a generic no-match result.
- [x] Focused Codex activation tests launch exactly one goal-bound specialist,
  waits exactly once, and persists a complete attestation.
- [x] Focused tests cover header reconciliation, atomic receipt persistence,
  hiring availability, and exact canary goal binding.
- [x] The named fast production spine and routing evaluation passed for the
  first merged repair; the follow-up focused set passes 67 tests and still
  requires the proportional fast spine before its live rerun.
- [ ] A fresh exact-installed Codex task visibly reports both resident managers,
  at least one accepted specialist for an explicit bounded work unit, and an
  authoritative provider/model receipt.
