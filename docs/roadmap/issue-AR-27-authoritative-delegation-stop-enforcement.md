---
title: "AR-27: Make delegation and Stop enforcement authoritative"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-18
tags: [delegation, hooks, evidence, correlation, reliability]
related:
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0011-explicit-delegation-evidence-lifecycle.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/roadmap/issue-AR-30-preserve-noun-phrases-in-work-unit-detection.md
  - docs/roadmap/issue-AR-69-require-correlation-complete-cli-delegation-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-27
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/28"
depends_on: [AR-25]
blocks:
  - AR-33
  - AR-58
  - AR-59
  - AR-69
  - AR-79
  - AR-87
---

# AR-27: Make delegation and Stop enforcement authoritative

## Problem

The public delegation tool describes and returns a delegation record while
persisting only a suggestion. Host tool normalization does not recognize the
actual public MCP tool name and common sanitized forms. Separately, a Stop retry
marked as hook-active bypasses verification entirely, allowing a malformed or
spoofed replacement header to escape the evidence gate.

## Current state

Public and CLI delegation mutations now require complete turn, work-unit,
backend, worker-kind, worker, and native-run identity before recording a
positive execution state. Recommendations remain immutable and distinct from
observed workers. Stop retries revalidate the current trace and terminal
correlation, every host uses a bounded continuation contract, and model receipt
callbacks cannot close the parent turn. Exact prompt retrieval is linked to one
single-use work-unit activation receipt while unauthenticated MCP execution
retains truthful generic-worker attribution.

## Approach

Require trace, session, and stable work-unit correlation for delegation mutation.
Normalize native and sanitized public tool names to one execution contract,
record concrete success, failure, and skipped states from observed results, and
keep suggestions distinct from execution. Revalidate every Stop retry against
current-turn evidence while enforcing a bounded continuation policy that cannot
loop indefinitely or silently accept contradictory claims. Reconcile host-native
run identifiers back to planned work-unit identities, persist each work-unit
transition atomically, and make failure sticky when callbacks arrive out of
order. Use each host's documented terminal control; where a host exposes only a
bounded revision primitive, record and disclose that residual limitation rather
than claiming a permanent deny capability. Treat model-call receipts as evidence
mutations rather than turn-terminal events, byte-bound every native rejection,
fail closed on oversized Stop envelopes, and preserve the host's authoritative
retry indicator. Treat tool identity as an authority boundary: accept only
explicit Agency and host-native identifiers, never an arbitrary namespace
whose final component resembles an Agency tool. Bound every supplied turn
correlation identifier to printable, control-free UTF-8 text before indexed
lookup or persistence. Project OpenClaw evidence into a bounded bridge envelope
and settle child standard-input errors without exposing an unhandled `EPIPE`.
Preserve the planned recommendation as immutable data, record host worker and
native run identities in separate fields, and require a one-use work-unit
activation capability plus reciprocal native execution receipt before exact
specialist-capability retrieval is accepted. Bind each receipt to the exact
ready-recipe slug, version, and hash; completion rejects partial activation
across the selected reference set. Keep execution attribution at
`generic-worker` because the current MCP transport does not authenticate the
retrieving caller as the native child.

## Dependencies

This implements the existing delegation lifecycle in ADR-0011 and the correlated
evidence boundary in ADR-0027. It uses AR-25's current-turn evidence query.

## Acceptance

- [x] Public delegation mutations require session, trace, and work-unit identity.
- [x] Successful public delegation records executed evidence, not a suggestion.
- [x] Failed and skipped results remain visible and are never promoted to success.
- [x] Public, sanitized, and legacy delegation tool names normalize consistently.
- [x] Stop retries are revalidated against current-turn authoritative evidence.
- [x] Retry enforcement is bounded and proven not to recurse indefinitely.
- [x] Native delegation IDs reconcile to one canonical planned work unit.
- [x] Planned recommendations are never overwritten by observed worker identity.
- [x] Native worker kind, worker ID, and native run ID remain independently auditable.
- [x] Exact specialist capability retrieval requires a linked one-use activation receipt.
- [x] Current MCP-backed execution retains generic delegated attribution even with a receipt.
- [x] Completion rejects partial, replayed, stale-version, or mismatched specialist activation.
- [x] Concurrent and reordered callbacks cannot duplicate or manufacture success.
- [x] Verification-storage failures block or revise on every host surface that exposes that control.
- [x] LiteLLM callbacks cannot close the Agency turn before central finalization.
- [x] Oversized or malformed native Stop envelopes cannot collapse into pass-through output.
- [x] Model-controlled delegation identifiers and serialized rejection messages are bounded.
- [x] Namespace suffix collisions cannot fabricate specialist, skill, or delegation evidence.
- [x] Supplied correlation identifiers are printable and bounded to 512 UTF-8 bytes.
- [x] Oversized OpenClaw tool results and early child exit reject without an uncaught host error.
- [x] OpenClaw uses its documented retry-active signal and rejects missing finalize content.
- [x] Hermes registers its documented code-edit `pre_verify` gate, consumes one
      retry, and binds any terminal safe replacement to a fresh evidence revision.
- [x] Hermes session-end cleanup closes only the exact interrupted or abandoned
      turn; session-only ambiguity closes none and terminal state is immutable.
- [x] Host contracts without terminal denial are documented as a residual limit.
- [x] End-to-end host-hook, MCP, evidence-integrity, and full validation pass.
