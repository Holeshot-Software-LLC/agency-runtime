---
title: "Construct evidence headers before first publication"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-08-22
tags: [evidence, finalization, headers, native-hosts, openclaw, hermes]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-277-keep-openclaw-finalization-first-pass.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0089-zcode-stop-rejections-use-decision-block.md
  - README.md
  - docs/THREAT_MODEL.md
supersedes:
  - docs/decisions/0071-bound-native-delegation-correction.md
superseded_by: null
id: ADR-0120
type: decision
deciders: [maintainers]
---

# ADR-0120: Construct evidence headers before first publication

## Context

Agency previously let a host emit a natural response, rejected a missing or
stale evidence header at finalization, and asked the model for one corrective
pass. That could make a structurally repaired header look healthy even when no
specialist launched, added latency, exposed host continuation prompts, and
occasionally entered a repair loop. A correction count greater than zero is
already a failed product trial, so a successful correction was not a useful
success state.

The runtime has authoritative Store evidence before the parent publishes its
answer. Supported hosts expose different pre-publication surfaces, but none
requires Agency to infer or repair evidence after the answer is visible.

## Decision

Construct the exact seven-field Agency header from current correlated Store
evidence before the first visible response:

- Native Codex receives an initial snapshot at `UserPromptSubmit`, an updated
  snapshot after recorded tools, and a final snapshot after a successful native
  wait. Later snapshots supersede earlier snapshots for the same turn.
- Hermes and OpenClaw preflight instruct the model to call the local
  `agency.finalize` tool exactly once immediately before its natural final
  response and emit the returned text byte-for-byte. The tool constructs the
  response from Agency's Store; it does not send a channel message and is not a
  post-response correction. Hermes may commit its text response at that
  boundary. OpenClaw leaves the constructed text pending until its final-only
  reply-payload gate atomically commits the complete outbound-envelope hash and
  separate policy-text hash. The host must emit the returned text as its
  natural final response, never a silent-reply sentinel.
- Every snapshot and finalizer result comes from the correlated Store. Failure
  to produce an exact snapshot supplies no guessed header.

The first invalid natural response is terminal. Persist `response_invalid`, or
`delegation_declined` when a strongly preferred delegation remains unresolved,
and never claim a continuation receipt or request another model pass. Native
Codex and Claude use the host lifecycle stop shape; ZCode retains its required
`decision:block` wire shape. OpenClaw remembers the terminal rejection and its
outbound seal cancels publication. Hermes replaces an invalid draft only with a
bounded safe failure response. A blocked or replaced draft is a failed turn,
not a corrected success.

Retain `retry_exhausted` only for reading historical finalization records. New
production header enforcement does not create it.

## Consequences

- A successful turn has `correction_count = 0` by construction.
- The displayed header remains a projection of recorded activity, not proof by
  itself that selection, launch, delegation, or model execution occurred.
- A malformed or stale response fails immediately and cannot become successful
  through a hook-generated continuation.
- Host adapters must prove both first-pass construction and terminal failure
  behavior against their exact supported lifecycle surfaces.
- Provider semantic repair during workforce inference remains a separate,
  bounded inference operation; it is not response-header correction.

## Alternatives

- **Keep one corrective response pass.** Rejected because it adds latency,
  obscures the first-pass failure, and can make presentation look healthier
  than execution.
- **Let the final hook rewrite the natural answer.** Rejected because the host
  may already have exposed the draft and the rewrite would still be a
  correction.
- **Publish an invalid response with a warning.** Rejected because unsupported
  activity claims must fail closed.
- **Generate a deterministic fallback header without Store evidence.** Rejected
  because absence of evidence cannot authorize runtime claims.
