---
title: "Separate Codex hook parent and child identities"
status: accepted
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, native-child, correlation, artifacts, security]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/child_delivery_evidence.py
  - tests/test_canary_activation_snapshot.py
  - tests/test_child_delivery_evidence.py
  - CHANGELOG.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
superseded_by: null
id: ADR-0188
type: decision
deciders: [maintainers]
---

# ADR-0188: Separate Codex hook parent and child identities

## Context

ADR-0187 correctly chose the exact host-authored child rollout as the lineage
authority, but it interpreted the two identifiers in Codex `0.149.1`'s
`SubagentStart` envelope incorrectly. The first exact rebuilt transaction with
that implementation produced a valid child `session_meta` and an accepted live
parent route, yet the child still received only generic identity context.

The supported Codex implementation constructs `SubagentStart.session_id` from
the session's root identity and `SubagentStart.agent_id` from the spawned
thread identity. The child rollout independently records the spawned thread in
its record and filename and the root parent in three agreeing lineage fields.
Requiring the two hook fields to be equal therefore rejects every genuine
depth-one child before the valid artifact can authorize its parent join.

## Decision

For the restricted current-profile Codex activation canary, treat the hook
`session_id` as the claimed root parent and `agent_id` as the claimed child.
Both must be canonical UUIDv7 values and must remain distinct. The exact
bounded, owner-trusted, version-pinned child rollout and its leading
`session_meta` must bind its filename and child record to `agent_id`; all three
host-authored parent fields must agree with one another and with the hook
`session_id`.

Only that four-way parent agreement scopes Store lookup. Exactly one live trace
in that parent session must still satisfy the complete accepted fixed-unit
activation route and ready, nonterminal run contract. A present request digest
must still equal the route query hash and run fingerprint. The child hook's
turn identifier is not parent-turn authority. Start continues to use
`transcript_path`; stop continues to use `agent_transcript_path`.

Every hook ID, artifact child, lineage parent, route, run, or digest mismatch
fails closed to the existing unstaffed identity. The join still grants no
specialist-selection, delivery, consumption, or finalization authority by
itself.

## Consequences

The correlation contract now matches the exact supported host protocol while
remaining stricter than either hook fields or artifact lineage alone. A caller
cannot redirect a valid child artifact to another hook parent, and a different
child cannot reuse that artifact. Concurrent turns inside one parent session
remain ambiguous and fail closed.

Codex identifier or rollout-format drift stops staffing until reviewed. The
private owner and supported Codex process remain the residual artifact-author
trust boundary already accepted by ADR-0156.

## Alternatives

Keeping `session_id == agent_id` was rejected by the exact rebuilt live failure
and the supported host construction. Trusting hook `session_id` without the
rollout was rejected because it would make a caller claim authoritative.
Trusting only the rollout parent was rejected because it would discard an
independent hook-to-artifact agreement. Using the child turn identifier as the
parent trace was rejected because Codex scopes it to the child turn.
