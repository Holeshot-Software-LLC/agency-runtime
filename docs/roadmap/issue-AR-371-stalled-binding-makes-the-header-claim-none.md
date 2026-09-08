---
title: "AR-371: A stalled binding acknowledgement makes every later turn report 'loaded: none'"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-07
tags: [resident-managers, header, evidence, fail-open]
related:
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0152-fail-open-with-honest-header-when-no-specialist.md
  - docs/roadmap/handoffs/issue-AR-371.md
  - docs/roadmap/acceptance/evidence/AR-371-next-turn-binding-recovery-20260907.md
  - agency_runtime/core/store/resident_binding.py
  - tests/test_resident_binding_recovery.py
  - docs/roadmap/issue-AR-367-fail-open-resident-binding-claim.md
  - docs/roadmap/issue-AR-357-canonical-response-contract-statement.md
  - docs/roadmap/issue-AR-369-stale-host-process-serves-a-superseded-kernel.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-371
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/521
depends_on: []
blocks: []
---

# AR-371: A stalled binding acknowledgement makes every later turn report 'loaded: none'

## Problem

The operator observed that the header reads `Agency/Agencies loaded: none`
on turns whose context visibly carries
`[Agency resident managers active; ... managers=agency-steward]`. A resident
steward is bound on every turn, so "none" is not a display quirk; it is the
header stating something false about the turn it describes.

Measured on this box 2026-09-02:

- `agency-steward` appears in **0 of 559** `specialists_loaded` rows. The
  steward is never recorded as loaded.
- `fill_header_fields` derives `agencies_loaded` from the evidence snapshot,
  whose `resident_managers` comes from the preflight recipe's binding kernel
  slugs. A fail-open turn has no ready recipe.
- AR-367 added the bridge: `_pending_resident_manager_binding_projection`
  rebuilds the binding a fail-open turn claimed. It requires
  `delivery_state == "pending"` **and** `pending_trace_id == trace_id`.
- This session's row is stuck: `delivery_state=pending`,
  `pending_trace_id=3a632dad-49da-4075-8380-6d5a33ed9499` — a trace that is
  not among the session's last five turns (`712e1832`, `b1fa965d`,
  `9375d19b`, `fe909461`, `17d5a49e`).

So once an acknowledgement stalls, the claim stays pinned to that dead trace,
every later turn in the session fails the exact-trace check, `resident_managers`
projects empty, and the header reports `none` for the rest of the session.
The failure is self-perpetuating and silent.

## Current state

2026-09-07 continuation: step 2 has a reviewed source candidate and 36 new
real-Store cases. Recovery moves an older closed pending claim
only to a different, strictly newer, latest run in the same host/session, at
that incoming run's own ready or fail-open claim boundary. The full existing
binding CAS still owns the write; it neither releases an unclaimed window nor
manufactures acknowledgment/reuse. Same-turn read/plan calls do not recover a
claim merely because fail-open closed the run before Stop.

The existing fail-open lifecycle regression now describes that intentional
next-turn recovery and preserves the delayed old Stop/new Stop distinction.
Active, unknown, missing, malformed, out-of-order and wrong-scope run evidence
stays refused. Kernel/control-epoch/generation checks are unchanged. Static
Ruff lint/format and diff checks pass. The owner's wrap-up authorization reopened
focused execution: 46 tests passed in 11.90s, with no preceding failed attempt.
Bounded independent source review reported no remaining scoped finding. Broad
suite, isolated acceptance and installed native delivery remain pending. No CI,
model/provider call, native operation or owner Store mutation ran in this package.

### Preserved historical state

Another session's row on the same host reached `acknowledged`, so the
lifecycle does work; this issue is that a stall in it is unbounded and
corrupts an evidence field rather than being reported.

## Approach

Two independent defects, and the first does not depend on fixing the second:

1. **Record delivery per turn, not per session lifecycle.** The steward was
   loaded into a turn if its kernel was delivered into that turn's context —
   a fact `_fail_open_preflight_result` already computes
   (`loaded_specialists=resident_managers`) and then discards. Persisting it
   with the turn makes the header read a per-turn fact instead of
   reconstructing one from a session-scoped state machine that can stall.
   This manufactures no evidence: it records what was actually delivered.
2. **Bound the stall.** A pending claim pinned to a trace that has already
   closed should be reported and released rather than pinning the session
   forever. A binding whose `pending_trace_id` names a closed run is a
   diagnosable state, not a permanent one.

## Dependencies

- AR-367 owns the fail-open claim this builds on.

## Implementation (2026-09-02), step 1

`Store.delivered_resident_manager_slugs` reports the resident managers a
fail-open turn was actually given, read from the durable binding row rather
than from the recipe (which the fail-open close erases) or the pending claim
(which one stalled acknowledgement pins to a dead trace). The completion
evidence snapshot falls back to it only when the earlier sources are empty,
so a ready turn and an acknowledged claim are untouched.

It is deliberately narrow, and each bound is a recorded fact rather than an
inference:

- only a run that closed `preflight_failed`, because that is exactly the turn
  the fail-open capsule answered, and that capsule always carries the kernel;
- only a persistent host, because a request-scoped host proves delivery per
  request and must keep doing so;
- only a binding row on the current contract.

Step 2 was still open at the 2026-09-02 checkpoint. Its 2026-09-07 source
implementation below is not yet accepted completion.

## Implementation (2026-09-07), step 2 candidate

Inside the already-held ready/fail-open write transaction,
`_closed_pending_claim_can_move` checks both exact run identities, an explicitly
recognized terminal old status with a valid bounded aware end timestamp, and
positive increasing durable turn sequences. The incoming run must be latest
for the same canonical host/session and be active/in-progress or just closed
preflight_failed with a valid end timestamp.
An existing verified HMAC session tombstone lookup prevents retention from
making an older candidate latest again. Since tombstones have no host field,
newer retired turns in the same session conservatively refuse recovery even
when they originated on another host; unrelated sessions and older tombstones
do not block. No new identity fields or schema writes are introduced.

`_commit_current_binding` then uses its existing state compare-and-swap to
retarget pending/last trace fields while preserving delivery mode and the
claimed restore generation. A newer compaction remains outstanding after that
delivery is acknowledged. The new claim remains pending until its own exact
Stop; a delayed old Stop or old claim cannot acknowledge or overwrite it.
Planning/read projections and request-scoped hosts gain no mutation path.

This implements the existing resident lifecycle under ADR-0122/ADR-0152,
not a new staffing authority, timer, acknowledgment inference or header fallback.
Unknown terminal vocabulary and missing/retired run proof remain closed rather
than guessing that an old claim is safe to steal. The original acceptance text
and proof boxes are retained, without a new satisfied verdict.

## Acceptance

- [x] A turn that received the resident-manager kernel reports it in
      `Agency/Agencies loaded`, whether or not preflight reached ready and
      whether or not the previous acknowledgement completed. Evidence:
      `Store.delivered_resident_manager_slugs`, its snapshot fallback, and
      `tests/test_resident_manager_header_honesty.py` --
      `test_a_fail_open_turn_names_the_steward_it_was_given` and
      `test_a_stalled_acknowledgement_does_not_silence_later_turns`.
- [ ] A pending claim whose trace has closed is released or reported, so one
      stalled acknowledgement cannot silence the rest of the session.
- [ ] A regression test pins that a fail-open turn following a stalled
      acknowledgement still names the steward.
