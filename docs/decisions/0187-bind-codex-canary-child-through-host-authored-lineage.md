---
title: "Bind the Codex canary child through host-authored lineage"
status: superseded
category: decisions
created: 2026-08-27
updated: 2026-08-27
tags: [codex, canary, hooks, native-child, correlation, artifacts, security]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
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
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
superseded_by: docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
id: ADR-0187
type: decision
deciders: [maintainers]
---

# ADR-0187: Bind the Codex canary child through host-authored lineage

## Context

ADR-0186 projected the SHA-256 of the nonce-bearing canary task into the Codex
process and expected each child lifecycle hook to retain that capability. The
exact `c7f35dd5` rebuild proves the parent task and Store route share the right
digest, yet `SubagentStart` still returns only the generic identity and creates
no child route. A process-level digest is therefore not sufficient live proof
of the child-to-parent edge on Codex `0.149.1`.

The same host-authored child rollout that later proves card delivery begins
with a `session_meta` record. In the exact supported profile it identifies the
child in the record and filename, identifies the parent independently in three
fields, records depth one and MultiAgent V2, and pins the host version and
`codex_exec` origin. The hook envelope supplies the canonical child transcript
path at start and the canonical agent transcript path at stop.

## Decision

For the restricted current-profile Codex activation canary, resolve a child
parent only from the exact leading host-authored `session_meta` in the active
Codex sessions root. The reader is version-pinned to `0.149.1`, bounded,
link-resistant, owner-trusted, and filename-bound. It requires the hook
`session_id` and `agent_id` to be the same canonical child UUID; the record and
filename must name that child; and the record's `session_id`,
`parent_thread_id`, and nested thread-spawn parent must be the same distinct
canonical UUID. It also requires `codex_exec`, paginated history, MultiAgent
V2, depth one, the exact child agent metadata, and no inherited parent history.

The authenticated parent UUID scopes Store lookup. Exactly one live trace in
that parent session must satisfy the complete accepted fixed-unit activation
route and ready, nonterminal run contract. A present lowercase request digest
must equal the route query hash and run fingerprint; a missing digest neither
selects a global run nor defeats the host lineage. Start uses
`transcript_path`; stop uses `agent_transcript_path`.

Every path, metadata, version, UUID, parent, route, run, or digest discrepancy
fails closed to the existing unstaffed identity. The lineage admits only a
parent edge. It does not choose a specialist, prove delivery, consume a grant,
or replace the independent host-artifact verification receipt.

## Consequences

Correlation no longer depends on undocumented child environment retention and
never chooses the globally sole open canary. Concurrent parents remain
separated by host-authored lineage, while concurrent turns inside one parent
session remain ambiguous and fail closed. Codex format or version drift stops
staffing until reviewed rather than silently widening authority.

This trusts the private owner account and the supported Codex process to author
its rollout, the same residual boundary already accepted for delivery proof.
It does not defend against a compromised owner or host forging its own files.

## Alternatives

Keeping the digest as the sole join was rejected by the rebuilt live failure.
Selecting the only open Codex run globally was rejected as ambient authority.
Parsing the encrypted assignment was rejected because the hook does not expose
it. Treating the child's exit or generic identity as delivery was rejected by
ADR-0156. Requiring a new Codex feature was rejected because the exact existing
host artifact already carries the independently authored parent edge.
