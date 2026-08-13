---
title: "Authenticate Codex plaintext spawns from host transcripts"
status: accepted
category: decisions
created: 2026-08-12
updated: 2026-08-13
tags: [codex, native-child, hooks, transcripts, security, evidence]
related:
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/THREAT_MODEL.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_spawn_provenance.py
  - agency_runtime/core/store/maintenance.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0159
type: decision
deciders: [lkrammes]
---

# ADR-0159: Authenticate Codex plaintext spawns from host transcripts

## Context

Codex 0.147 supports two MultiAgentV2 delivery modes. A collaboration function
call whose host response item contains explicit `encrypted_function_args: []`
is delivered as plaintext; a call without that exact marker remains encrypted.
The current Sol/TUI observation used the encrypted path.

Codex `PreToolUse` exposes the transcript path, session, turn, tool-call ID, and
parsed arguments and can replace local function-tool arguments. It does not
expose the plaintext marker or internal tool-call source. Trusting
`tool_input.message`, `task_name`, a model slug, or ciphertext appearance would
therefore let model-authored input impersonate host-authorized plaintext.

The host records the complete function-call response item before queuing tool
execution, so the parent transcript is the available pre-dispatch source for
the missing provenance. Codex documents that transcript format as unstable.
Any parser is consequently a version-pinned compatibility boundary, not a
generic JSONL trust grant.

## Decision

Agency may rewrite a Codex native-child `spawn_agent` message only after a
sealed in-process attestation proves one exact host-persisted plaintext call.
The first supported capability version is exact Codex CLI `0.147.0`; every
unknown version or schema fails open unstaffed.

The attestor accepts only the canonical active transcript beneath the private
Codex sessions root. It rejects relative or caller-selected roots, links,
Windows reparse points, hard links, mutable non-owner access, replacement,
truncation, oversized input, duplicate keys, and unstable descriptor/path
identity. A purpose-built bounded streaming scanner must support observed large
rollout lines without loading the transcript as one object.

The transcript must have one matching root session identity and exactly one
`response_item.function_call` with namespace `collaboration`, name
`spawn_agent`, the hook's session, turn, and call IDs, arguments exactly equal
to the complete hook input, and `encrypted_function_args` present as exactly an
empty list. Null, missing, nonempty, ambiguous, stale, completed, or replayed
calls are unstaffed. V1 receives no implicit exception.

Attestation returns only sealed, content-free identities and digests. Agency
revalidates the exact file and records during the existing delivery validator
and again immediately before returning `updatedInput`. The Store transaction
atomically rejects a second native-child inference delivery for the same host,
parent session, parent trace, and launch ID so concurrent hooks cannot obtain
two rewrites.

This attestation authorizes only the pre-spawn rewrite. It cannot prove that the
child received or used the cards. ADR-0156 remains the sole Rule-4 authority: a
green result still requires the host-authored child artifact with every exact
inference-selected card hash before first child speech. Installed and Live
claims additionally bind the exact Codex executable and Agency candidate.

## Consequences

- Current encrypted Sol calls continue unstaffed without blocking native host
  execution.
- A marked plaintext call can use the existing inference-owned multi-card
  staffing path without trusting a model-authored label or message.
- Codex transcript or version drift becomes an explicit compatibility failure
  and requires a reviewed capability update.
- The new scanner and one-use transaction need focused spoof, replay, path,
  schema, size, concurrency, and TOCTOU tests before installation.
- Source and simulation can advance independently; neither changes an Installed
  or Live matrix layer.

## Alternatives

- **Trust a plaintext-looking hook message.** Rejected because the hook does not
  expose whether the host selected plaintext delivery.
- **Use `task_name`, model slug, or message shape as authority.** Rejected
  because those values are model-authored or merely heuristic.
- **Inject cards at `SubagentStart`.** Rejected because that event does not bind
  its context to the exact authenticated parent spawn call.
- **Treat the transcript as a generic stable interface.** Rejected because the
  host documents it as unstable; exact version and schema pinning are required.
- **Wait indefinitely for a richer upstream hook field.** Rejected as the only
  path because the exact host already persists sufficient bounded provenance;
  a future direct marker may supersede this compatibility adapter.

## Provenance

The 2026-08-12 AR-180 read-only preflight identified Codex CLI `0.147.0`,
Desktop runtime `0.147.0-alpha.6.6`, the conditional marker contract, and one
current encrypted Sol/TUI spawn. It ran no Agency canary and changed no install
or trust state.

Candidate `966845cc` implements this boundary with a bounded descriptor scanner,
sealed record identities, repeated revalidation, and an atomic successful-launch
guard. Adversarial review found incomplete nested-thread ancestry and a
post-persistence final-validation gap; source and simulation remain negative
until those defects are repaired. Installed and Live proof remains unproven.
