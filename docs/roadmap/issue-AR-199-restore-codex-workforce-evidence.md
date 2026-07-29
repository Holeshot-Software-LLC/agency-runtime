---
title: "AR-199: Restore Codex workforce selection and evidence"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-29
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
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161
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

Exact installed revision `f2f901d9d85fbe63d413ccc9d3bf01c976bcee2e`
successfully registers Codex and ZCode. The three merged repair slices now
commit workforce receipts and deferred hires atomically, preserve Codex's
encrypted spawn input, and inject the exact specialist context at child start.

A fresh USB-diagnostic task proved that inference is running: two provider
attempts were recorded against `codex-subscription/gpt-5.6-luna`. The active
roster still produced zero eligible workers, and governed hiring declined with
`contract_invalid:ValueError`. The parent Codex task was configured by the
owner as Sol High; Luna was only Agency's independently configured workforce
planner. The existing `Actual Model selected` projection therefore conflated
three distinct identities: parent task, workforce inference, and specialist
execution.

Source reproduction isolated the hiring failure. The hiring JSON schema accepts
natural-language artifacts and safety boundaries, while the workforce contract
requires exact normalized artifact, lifecycle, capability, tool, host, and
platform identifiers. A generated contractor could therefore be valid prose
but fail its own causing work unit or current host.

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

The current follow-up binds every validated employment contract to the exact
typed causing work unit before criticism and persistence. It also aligns the
provider JSON schema with the parser, keeps natural-language artifact prose out
of typed routing identifiers, accepts explicit negative safety boundaries, and
passes the current host into deterministic eligibility. Header model text now
labels matching provider receipts as workforce inference and explicitly states
that the parent model is host-selected and not observable to Agency; it never
promotes Luna into the parent or specialist slot.

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
- [x] The current hiring and model-scope follow-up passes 177 broadened focused
  tests with one expected xfail; all 601 Python files pass Ruff.
- [ ] A fresh exact-installed Codex task visibly reports both resident managers,
  at least one accepted specialist for an explicit bounded work unit, and an
  authoritative provider/model receipt.
