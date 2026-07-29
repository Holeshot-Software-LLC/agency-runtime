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

Exact installed revision `34e3180e465c175b07e1b0ae3c0b14106c36cca2`
successfully registers Codex and ZCode. The merged repair slices now
commit workforce receipts and deferred hires atomically, preserve Codex's
encrypted spawn input, inject the exact specialist context at child start, bind
generated contractors to their causing unit, and keep parent, planner, and
specialist model scopes distinct.

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

The first source-level isolated canary after PR 162 proved the remaining route
regression exactly: its predecessor planned two units and selected nobody,
whereas trace `019fae5a-4815-7a82-a65e-66db8e35f203` used
`codex_activation_canary_contract`, selected `code-reviewer`, emitted one unit,
spawned once, and waited once. The child started and completed, but Codex's
spawn result left the issued activation grant unconsumed and the specialist-load
receipt absent. Exact-installed reruns after PRs 163 and 164 disproved both the
mapping-only and optional-nickname diagnoses: this configured Codex v0.146
surface emitted exactly `{"task_name":"/root/unit_05d45f7553"}`. The live
ordering instead records and delivers the real child at SubagentStart while the
grant remains deferred to PostToolUse. After moving consumption to
SubagentStart, traces through `019faeca-406f-7d20-b2e7-6b1741b5a8af` proved
that PostToolUse does not resolve the original callback identity: the consumed grant and real
child remained authoritative, but the compact delegation retained its
synthetic task label and finalization correctly stopped at `continue`.

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

The isolated canary backend now marks its existing evidence Store before the
nonce-bound request. The PostToolUse boundary accepts Codex's native mapping
shape as well as its JSON-string shape. For v0.146 spawn results it permits only
`task_name` and the documented optional `nickname`, discards the nickname before
binding, and retains the rooted task label, exact task-name, exact projected-key,
persisted child-lifecycle, and one-use activation checks.

The current follow-up consumes the opaque canary's exact native-hook grant at
SubagentStart, after the real child UUID lifecycle is persisted and before the
specialist context is returned. Exact tool-use, unit, specialist version, prompt
hash, prompt body, worker, and native-run identities must all match. PostToolUse
then reconciles the already-consumed lineage idempotently.

Source-live trace `019faea3-4ea3-73a1-86c7-73443e519dc8` proves that repair:
one activation consumption and one specialist load now bind the real Codex
child UUID. The remaining verifier failure is limited to Codex's exact
`--dangerously-bypass-hook-trust` notice being counted as an unexpected tool.
The parser now excludes only that fixed host notice and rejects all other error
items.

PostToolUse now reconciles a missing host callback only when the Store already
contains exactly one consumed native-hook activation for the exact planned task
label, selected specialist version/hash, and real `codex-agent:<UUID>` child.
It validates Codex's bounded rooted response before replacing the synthetic
task projection; unconsumed, ambiguous, mismatched, or synthetic lineage still
fails closed. A focused callback-ID rewrite regression joins the complete
activation suite, which passes 17 tests.

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
- [x] Source-level isolated canary routing selects exactly `code-reviewer`,
  produces one read-only unit, spawns once, and waits once without a trust
  prompt; focused activation and receipt verification passes 68 tests with two
  platform skips.
- [ ] A fresh exact-installed Codex task visibly reports both resident managers,
  at least one accepted specialist for an explicit bounded work unit, and an
  authoritative provider/model receipt.
