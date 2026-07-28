---
title: "AR-191: Support the Codex V2 native-spawn hook identity"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [codex, hooks, activation, canary, observability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/THREAT_MODEL.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/cli/install_commands.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/installer_contracts.py
  - agency_runtime/core/installer_payloads.py
  - agency_runtime/core/store/delegation_activation.py
  - tests/test_codex_activation_canary.py
  - tests/test_delegation_activation_receipts.py
  - tests/test_host_hooks.py
  - tests/test_host_canary.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-191
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-180]
---

# AR-191: Support the Codex V2 native-spawn hook identity

## Problem

Codex 0.145 MultiAgentV2 exposes `spawn_agent` in the `collaboration`
namespace, but its command-hook envelope flattens that pair to
`collaborationspawn_agent`. Agency Runtime installed and accepted only the
older `spawn_agent` identity. The parent therefore followed its exact Agency
plan while `PreToolUse` never injected the specialist activation envelope; the
child received only generic identity context and incorrectly delegated again.

The same live attempt exposed two evidence defects. `SubagentStart.turn_id` is
the child turn rather than the routed parent trace, and a successful Codex
process whose bounded output projection is unavailable was reported with a
synthetic exit code instead of its real process result.

## Current state

The candidate enumerates both exact hook identities behind one anchored
matcher and maps both to the existing canonical `spawn_agent` evidence name.
It retains exact allowlisting and does not suffix-match arbitrary namespaces.
The live-shape regression preserves every original tool argument, including
`fork_turns`, while replacing only the child message with the exact specialist
delivery envelope.

Native-child lifecycle correlation now accepts a supplied trace only when the
Store proves it is an active run for the same parent session; otherwise it
recovers the sole active parent trace. Canary records preserve the real process
exit code and add a bounded reason when output, collaboration, or both
projections are unavailable. The public executed Agency/current-profile Codex
canary also requires the existing configured Store used by the installed hook.
Because Codex's flattened V2 hook name cannot prove the original namespace by
itself, its activation grant cannot be consumed until the same parent trace has
one unclaimed native-child start. The atomic Store check prevents a colliding
extension result from fabricating more activations than Codex lifecycle events.
Both installed Codex hook spellings require that lifecycle claim; a response
that supplies an agent ID must match that exact lifecycle identity. The
flattened name is never canonicalized for non-Codex hosts, and planned nested
denials are recorded as denied rather than successful hook responses. An
idempotent PostTool replay must also prove the exact consumed activation-token
digest and originating tool-use ID rather than borrowing lineage from the unit.
Codex's JSON-text spawn result is bounded-parsed without losing whether the host
actually supplied a child identity. A V2 result must contain a canonical root or
nested AgentPath; it is reduced to its validated leaf, and that leaf must equal
the exact persisted tool-input task name before the unique lifecycle receiver is
bound. Both reversible `unit_<digest>` and generated `agency_<digest>` labels
remain supported.

## Approach

Keep the compatibility surface explicit and shared between installation and
runtime handling. Exercise the exact current Codex V2 envelope through
`PreToolUse`, `SubagentStart`, `PostToolUse`, `SubagentStop`, and `Stop`, reject
lookalike names, and retain the existing advisory boundary: Agency may bind or
reject only a positively identified planned child and never replaces Codex's
native scheduler.

## Dependencies

AR-180 owns the live activation proof and AR-185 owns exact current-profile
verification. Tracker creation remains pending explicit authorization for the
outward-facing write.

## Acceptance

- [x] Generated Codex hooks match only the exact V1 and V2 native-spawn names.
- [x] Runtime canonicalization accepts both identities and rejects lookalikes.
- [x] A live-shape V2 regression preserves all non-message tool arguments and
  proves the complete activation/finalization chain.
- [x] Child lifecycle events bind to the active parent trace when Codex supplies
  a distinct child `turn_id`.
- [x] A flattened V2 result cannot consume an activation without a preceding,
  atomically unclaimed Codex native-child start on the parent trace.
- [x] Every installed Codex spawn spelling requires lifecycle proof; supplied
  child identities match exactly and replay is token/tool-use bound.
- [x] Projection failures preserve the actual process exit code and identify
  the unavailable proof surface.
- [x] Executed Agency/current-profile CLI canaries require the existing Store.
- [ ] One fresh installed current-profile canary proves the exact activation
  graph.

## Implementation evidence

The first focused package passed 30 warning-strict tests in 55.26 seconds; the
single corrected diagnostic expectation and the exact live-shape activation,
cross-process correlation regressions then passed 3/3 in 16.33 seconds. The
final named fast production spine passes 536 tests with 5 platform skips in
82.43 seconds. The final identity, replay, rooted-path, lifecycle, denial, and
canary package passes 12 warning-strict focused tests in 34.86 seconds; an
independent security re-review then passed four adversarial checks and reported
no AR-191 or live-canary blocker. All 109 dashboard UI tests and every routing,
delegation, and performance gate pass, and repository-wide Ruff lint and format
checks pass. One optional two-file sweep exceeded its three-minute cap without a
result and was not retried; its changed paths pass the focused tests. No
exhaustive suite or hosted workflow ran.
