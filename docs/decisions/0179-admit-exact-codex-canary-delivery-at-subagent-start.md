---
title: "Admit exact Codex canary delivery at SubagentStart"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-27
tags: [codex, canary, native-child, hooks, evidence, security]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/AR-180-codex-0149-compatibility-evidence.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0179
type: decision
deciders: [maintainers]
---

# ADR-0179: Admit exact Codex canary delivery at SubagentStart

## Context

Codex CLI `0.149.1` encrypts the native `spawn_agent` assignment before
`PreToolUse`, so ADR-0159 correctly keeps ordinary native children unstaffed.
The repository-owned current-profile activation canary has a narrower source of
authority: before the host creates the child, Agency has already persisted one
accepted inference route and one exact delegation-plan unit in the existing
Store. At `SubagentStart`, Codex supplies the host-created child UUID and
persists the hook's `additionalContext` as its own distinct developer message in
the child's canonical rollout before the child's first speech.

The first AR-309 live attempt proved that exact lifecycle but failed because the
reader concatenated every pre-speech developer and user message, could not
attribute the hook-owned message, and rejected all Codex v6 deliveries. Store
rows or the parent's later prose cannot replace the missing host artifact under
ADR-0156.

## Decision

Agency may staff at Codex `SubagentStart` only for its exact repository-owned
current-profile activation canary. Admission requires both
`AGENCY_CANARY_MODE=1` and `AGENCY_CANARY_REQUIRE_EXISTING_STORE=1`, a managed
no-bypass invocation, the ADR-0186 invocation digest, child `session_id` equal
to `agent_id`, exactly one active Store parent whose ready request fingerprint
matches that digest, the fixed activation work unit, one accepted
`code-reviewer` route whose source is `codex_activation_canary_inference`, and
one exact delegate plan row for that unit. The host-created child UUID is the
delivery's `child_id` binding and launch identity. Any absent, ambiguous,
stale, mismatched, terminal, or unsupported input returns the existing
identity-only unstaffed context.

The exact 0.149.1 MultiAgentV2 spawn keeps `task_name=code_reviewer` as the
child path and, because the optional explicit role is absent, reports the
built-in `agent_type=default` at `SubagentStart`. That value is only a pinned
host-schema discriminator: it never selects a specialist or work unit. A child
rollout that reports an explicit `agent_role` is not the exact canary shape and
fails closed.

The hook runs the ordinary configured inference-owned staffing transaction and
returns its complete v6 rewritten task as the sole `additionalContext` message.
It does not infer selection from `agent_type`, task labels, encrypted text,
model output, or parent prose. General Codex spawns and every non-canary
`SubagentStart` remain governed by ADR-0159 and receive no specialist.

For this bounded profile, a Codex rollout reader treats individual pre-speech
input messages as separate candidates. Exactly one complete v6 message must
match the Store decision, host parent UUID, child UUID, install identity, fixed
task hash, card hashes, and decision lifetime. Partial, combined, repeated, or
ambiguous markers fail closed. The canonical rollout must have an owner/root-
controlled, link-free, non-group/other-writable namespace and an owner-written
single-link file; host-selected read/traverse bits do not substitute for
mutation authority. The host timestamp and invocation window remain mandatory.
Only the internal canary
collector may classify that distinct `SubagentStart` message as structural hook
output and atomically persist or re-project the immutable one-use delivery
receipt; the public diagnostic reader cannot turn caller-supplied Codex text
green.

The successful wait hook reconciles the exact host child identity to the sole
planned delegation and records the verified delivery before producing the final
Store-backed header snapshot. The canary backend independently validates one
root rollout, one child rollout, one spawn/start/wait topology, and the same
invocation window before constructing the sealed proof consumed by final
attestation. A missing streaming parent ID or output may be recovered only from
exactly one canonical root rollout in that window.

## Consequences

Codex `0.149.1` can prove the card actually reached the sole activation-canary
child before speech without weakening the general encrypted-spawn boundary.
The repair depends on an exact, repository-owned canary contract and a
version-shaped host artifact, so Codex schema drift becomes an explicit canary
failure. Staffing happens after host child creation rather than by rewriting the
opaque parent call; the Store decision, child UUID, artifact, and receipt must
all agree before any delegated header or attestation can pass.

This decision does not authorize activation bypasses, arbitrary current-profile
artifact collection, caller-selected roots, generic SubagentStart staffing,
stable `multi_agent` synthesis, or replacing host evidence with Store state.
Installed and Live claims still require a fresh exact transaction.

## Alternatives

Returning a child-generated challenge was rejected because model output would
be a weaker origin than the host-persisted pre-speech hook message. Widening
ADR-0159's plaintext attestation was rejected because `0.149.1` still encrypts
the parent assignment. Trusting the child UUID or accepted Store route alone was
rejected because neither proves delivery. Continuing with stable `multi_agent`
was rejected because the live comparison produced no native delegation. A
generic Codex artifact verifier was rejected because only the exact managed
canary establishes the bounded structural origin needed for this exception.
