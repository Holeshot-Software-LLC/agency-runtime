---
title: "AR-371: A stalled binding acknowledgement makes every later turn report 'loaded: none'"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [resident-managers, header, evidence, fail-open]
related:
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

## Acceptance

- [ ] A turn that received the resident-manager kernel reports it in
      `Agency/Agencies loaded`, whether or not preflight reached ready and
      whether or not the previous acknowledgement completed.
- [ ] A pending claim whose trace has closed is released or reported, so one
      stalled acknowledgement cannot silence the rest of the session.
- [ ] A regression test pins that a fail-open turn following a stalled
      acknowledgement still names the steward.
