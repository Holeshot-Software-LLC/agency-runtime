---
title: "AR-252: Record host-evidenced, independently verified outcomes for automatic promotion"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-12
tags: [workforce, promotion, evidence, native-child, outcomes, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/workforce.py
  - agency_runtime/core/store/native_child.py
  - agency_runtime/core/workforce/promotion.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-252
priority: p0
tracker_url: null
depends_on: [AR-180, AR-242, AR-255]
blocks: [AR-119, AR-253]
---

# AR-252: Record host-evidenced, independently verified outcomes for automatic promotion

## Problem

The automatic contractor-to-employee policy is implemented, but its live
evidence path is dormant. Native child termination records an `assignment`
outcome without independent acceptance evidence, so production work cannot
satisfy `promotion_readiness` or trigger `_auto_promote_if_ready`.

The former proposal depended on retired Job B plan rows, assurance units, and
consumed activation receipts. Restoring that transport would contradict the
current host-spawned, just-in-time architecture.

## Current state

AR-242 set the three-success and seven-day review-window policy. Store code can
validate acceptance evidence and perform automatic promotion atomically, but no
current host-backed producer/verifier correlation emits the required event.
Agency-authored assignment rows alone are not proof of successful work.

## Approach

Build an outcome envelope from artifacts the native host wrote. Those artifacts
prove the producer/verifier children, delivered card hashes, artifact digest,
and correlation; they do not prove semantic correctness. A distinct governed
verifier selected by inference establishes semantic acceptance through its
verdict bound to that exact artifact. Store receipts remain a derived audit
index, not the delivery authority.

Evaluate promotion in the same transaction that persists the validated
acceptance. Keep the existing three-success threshold and per-contractor review
window. Do not depend on Job B, model-authored headers, Agency-only lifecycle
rows, or a shared producer/verifier identity.

## Dependencies

- AR-255 must establish inference-owned card choice and host-authored delivery
  proof before an outcome can be attributed to a specialist.
- AR-242 supplies the existing threshold and review-window implementation; its
  unchecked acceptance record is reconciled under AR-256.

## Acceptance

- [x] A host-backed producer artifact plus a distinct, inference-selected
      verifier's host-backed artifact and bound accepted verdict records exactly
      one acceptance event.
- [x] Missing, ambiguous, replayed, Agency-only, shared-identity, or rejected
      evidence records no acceptance and reports a bounded reason.
- [x] Three distinct accepted outcomes automatically promote an eligible
      contractor after its review window with `actor="promotion-policy"` and
      the exact evidence manifest; no operator action is required.
- [x] Replay and concurrent finalization cannot duplicate an outcome or
      promotion.
- [x] Migrate promotion validation and readiness from retired work-unit and
      consumed-activation-receipt identities to the host child, card hash,
      artifact digest, verifier decision, and verdict identities above.
- [ ] Live evidence proves the path through at least Claude and Codex before
      AR-119 can close.
- [ ] AR-253 proves the same accepted-outcome and automatic-promotion behavior
      on ZCode, Hermes, and OpenClaw; an unavailable supported host remains
      unproven and blocks AR-119.

## What the checked boxes do and do not mean

The five checked items are the host-free half: the rule that decides what may
count, the recorder that applies it, and the readiness migration. They are
proven by source and simulation in `agency_runtime/core/workforce/acceptance.py`
and `tests/test_accepted_outcomes.py`, which runs in CI.

They are not proof that the path runs. No host has yet produced a real envelope:
the producer and verifier proofs come from the sealed
`agency.host-child-delivery-proof.v1` projection, and in every case above they
are constructed by the test rather than collected from a Claude transcript or a
Codex rollout. The remaining two items are exactly that gap, and until they
close, the runtime can accept an outcome that nothing yet offers it.

The collector seam is `agency_runtime/core/child_delivery_evidence.py`, whose
`_host_child_delivery_projection` already emits the accepted proof shape for a
verified delivery. What is missing is the step that pairs one producer proof
with one verifier proof and that verifier's verdict, which is where the live
work starts.

## Measured before building the collector (2026-08-14, `9e29aabe`)

Three constraints found by reading the seam, and any collector design has to
answer all three. They are recorded here so the next attempt does not discover
them halfway through a build.

1. **Agency cannot summon the verifier.** Rule 5 gives spawning to the native
   harness alone, and `agency_runtime/core/evals/spawn_authority.py` proves at
   the source that worker origin is confined to the host boundaries. So a
   "distinct governed verifier selected by inference" is not something Agency
   arranges — it exists only when the *host* independently spawns a second child
   and Agency staffs it. The collector can recognise verification; it cannot
   cause it. An acceptance rate below 100% is therefore the expected steady
   state, not a defect, and the promotion policy has to tolerate that.

2. **The verified-delivery capability is one-use and canary-only.**
   `_consume_verified_host_child_delivery` pops its identity on read, and the
   sole production consumer is `agency_runtime/core/canary_proof.py`, which
   collects inside a disposable host profile under ADR-0158. Nothing today holds
   two such capabilities at once, which is exactly what one envelope needs.
   Widening the seal is a threat-model change, not a refactor.

3. **No child carries a producer/verifier role, and completion is not
   acceptance.** `record_native_assignment_outcome` maps a native child's exit
   to `passed`/`failed`; ADR-0157 rejects counting child exits precisely because
   completion is not semantic acceptance. Nothing records that one child's work
   was the subject of another child's judgement, so the correlation the envelope
   needs — verdict bound to the producer's artifact digest — has no producer in
   the runtime yet.

## A fourth constraint, found by reading the rule against the seam (2026-08-14)

The three above were found by reading the collector. This one falls out of the
acceptance rule itself and is the sharpest of the four.

`evaluate_acceptance` takes `artifact_digest` from `producer["artifact_digest"]`,
and `_host_child_delivery_projection` sets that field from
`evidence.artifact_digest` — the SHA-256 of the bounded trusted read window of
**the producer child's own transcript**. It is not a digest of any work product.
The verdict must then match it exactly (`verdict_artifact_mismatch`).

So the thing a verifier must bind its verdict to is the hash of a file it cannot
read: the producer's transcript lives in the host's namespace, and the verifier
child has no access to it. **No verifier can compute or even quote that digest
unaided.** Only the collector — Agency, after reading the producer artifact —
can supply it.

That does not make the envelope unbuildable, but it fixes the verdict's shape:
the *semantic* half (accept or reject) must come from the verifier child's own
host-written output, while the *binding* half (which artifact, which verifier)
is assembled by Agency around it. A verdict is therefore a joint object, and the
design has to say so out loud rather than let a reader assume the verifier
authored the whole thing. Whether that division is acceptable evidence, or
whether the rule should bind to a digest of the produced work instead, is an
open decision and not one to settle inside a collector build.

## Collector diagnosis shipped ahead of the collector (2026-08-14)

`_collect_private_host_child_delivery` answered eighteen distinct conditions
with a bare `None`, so a Rule 4 canary reported only that delivery "was not
proven". It now returns `HostChildCollection` with a closed reason vocabulary,
the canary record carries `host_child_collection_reason`, and the operator-facing
failure line quotes it. On a live run the same afternoon that previously said
nothing, it says `delivery_marker_absent`.

This is not the envelope collector and does not check any box above. It is the
instrument the envelope collector will be built with — every stage it now names
is a stage the pairing collector has to pass through twice.

What the instrument then found changes where the collector can live. **`claude -p`
runs no Agency hooks at all**: against the real profile, with no
`CLAUDE_CONFIG_DIR` override and every inherited `CLAUDE_CODE_*` variable
stripped, a headless run spawned a child that received no card and left
`runs: 0`, `routing: 0`, `receipts: 0`. Interactive sessions on the same machine
staff at confidence 1.0. Since the disposable-profile canary is built on `-p`,
**the producer proof this envelope needs cannot be collected there today** —
which is a prerequisite for this issue, not a detail of it.
