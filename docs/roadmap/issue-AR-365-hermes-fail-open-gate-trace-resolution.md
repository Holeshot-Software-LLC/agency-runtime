---
title: "AR-365: Hermes fail-open pass-through unreachable live — gate cannot resolve the closed run"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [hermes, fail-open, rule8, correlation, bug]
related:
  - docs/roadmap/issue-AR-346-hermes-fail-open-draft-replacement.md
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-365
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/440
depends_on: []
blocks: []
---

# AR-365: Hermes fail-open pass-through unreachable live — gate cannot resolve the closed run

## Problem

The AR-346 pass-through shipped and deployed, and the very first live
fail-open hermes turns still replaced the owner's answers with the
finalization block message. Measured 2026-09-01 20:10–20:13Z on the
owner's Telegram session (turn_sequence 899/900): both runs closed
`preflight_failed` — squarely inside `_FAIL_OPEN_RUN_STATUSES` — no
finalization event was recorded, and the block text was delivered
anyway, minutes after the deploy's batteries passed.

## Root cause

The turn's authoritative composite trace (`session:trace:suffix`) is
minted inside preflight and returned to the host wiring only in the
preflight *result*. The generated hermes plugin remembers that trace on
success (`_remember_preflight_result`) — but a failed preflight returns
no correlation, so at `transform_llm_output` time the wrapper falls
back to the host's raw trace or to nothing. In the bridge,
`resolve_turn_trace` returns an explicit trace verbatim and its
no-trace fallback (`get_open_traces_for_session`) filters to
`active`/`evidence_only` — a run already closed `preflight_failed` is
invisible on both paths. `_turn_closed_without_bound_response` therefore
never finds the closed run in production; the AR-346 branch was
reachable only by tests that handed it the composite directly.

## Fix (this change)

- New store read `get_latest_run_for_session(session_id)` — the most
  recently started turn parent for one session.
- `_turn_closed_without_bound_response` keeps the exact `get_run` path,
  then falls back to the session's latest run, bound to the provided
  trace when one exists (`stored == provided` or
  `stored.startswith(f"{session}:{provided}:")`); an unbound provided
  trace and any verdict-bearing status stay fail-closed.
- Regression tests pin both live shapes (host-raw trace, no trace) and
  both fail-closed guards (verdict-bearing latest run, unbound trace).

## Dependencies

- None. AR-356's disclosure line remains the complementary capsule-side
  honesty fix.

## Acceptance

- [x] A fail-open turn whose transform call carries only the host's raw
      trace passes the draft through unchanged (regression test).
- [x] A fail-open turn with no trace at all passes the draft through via
      the session-latest fallback (regression test).
- [x] Evaluated rejections and unbound traces keep the withhold
      semantics (regression tests).
- [ ] Deployed to the live hermes host and a real fail-open turn
      delivers the model's draft instead of the block message.
