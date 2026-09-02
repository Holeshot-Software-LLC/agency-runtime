---
title: "AR-366: OpenClaw withholds fail-open replies — evaluated rejection fires on turns staffing never reached"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [openclaw, fail-open, rule8, delivery, bug]
related:
  - docs/roadmap/issue-AR-365-hermes-fail-open-gate-trace-resolution.md
  - docs/roadmap/issue-AR-344-codex-fail-open-stop-terminal-exit.md
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
  - docs/roadmap/issue-AR-358-installer-doctor-trust-chain-self-healing.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-366
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/444
depends_on: []
blocks: []
---

# AR-366: OpenClaw withholds fail-open replies — evaluated rejection fires on turns staffing never reached

## Problem

An owner request on the Telegram channel produced no reply at all.
Measured 2026-09-01 20:29–20:33Z: the request turn (trace `142cfda4`)
failed open (`workforce_inference_failed`, the AR-353 window) and went
out unstaffed and headerless; the follow-up turn (trace `e40c487b`)
was withheld entirely — its finalization event records
`response_invalid` with all five header fields missing while the run's
`preflight_state` was still `in_progress` two seconds into the turn.
The user saw silence. Rule 8 forbids exactly this: the evidence was
missing because Agency's own staffing never completed, not because the
host misbehaved.

## Current state

`node_bridge._publish_unverified` already passes through when Agency is
*unavailable* (raise/correlation-loss paths). But the evaluated
rejection path (`_finish_policy_rejection` and kin) has no equivalent
of the hermes AR-365 gate: a policy rejection on a turn whose run
closed fail-open — or whose preflight never reached `ready` — defends
no bound response, yet still withholds the reply.

Compounding factors the same evening, recorded for AR-358's scope: the
2026.8.2 `--accept-capabilities` gap left the plugin disabled-in-config
from ~20:26 to 20:34, and a deploy-time gateway restart raised
`GatewayDrainingError` on a live turn.

## Approach

Give the openclaw rejection path the same run-status gate the hermes
bridge now has (`_FAIL_OPEN_RUN_STATUSES` + session-latest fallback,
AR-365), shared rather than copied a third time — the two-sources-of-
truth drift is what kept this alive on openclaw after the Stop path was
fixed. Design constraint: the naive "preflight incomplete → publish"
bypass is a verification loophole for responses that race preflight on
healthy turns; the gate must key on the run's terminal fail-open status
or on recorded preflight-failure receipts for the turn, never on mere
incompleteness. AR-356's disclosure line then makes the delivered
fail-open reply honest about being unstaffed.

## Implementation (2026-09-01, all-host sweep by owner directive)

Owner directive: "rule 8 needs to be applied for all harnesses … I need
to know it failed, but it can't get in the way." The gate now lives once
in `core/rule8_evidence.py` (`FAIL_OPEN_RUN_STATUSES`,
`turn_closed_without_bound_response` with the AR-365 session-latest
fallback, and `turn_never_received_staffing_contract`, which fires only
for an `active` run whose `preflight_state` is exactly `in_progress` —
live data confirms staffed turns on all four hosts read `ready`, so
verification keeps its teeth) and is applied at every rejection outlet:

- hermes `bridge._turn_closed_without_bound_response` delegates to it
  (AR-365 semantics unchanged);
- openclaw `node_bridge` publishes via `_publish_unverified` when a
  closed run is fail-open (was: terminal mismatch) and via
  `_agency_fault_pass_through` before `_finish_policy_rejection` (the
  measured 20:32Z race shape);
- the shared claude/codex/zcode Stop path (`adapters/hooks.py`) gates
  both the `_is_terminal_turn` branch — the AR-344 `continue:false`
  terminal-exit shape — and the evaluated-rejection branch, publishing
  with reasons `turn_closed_fail_open` / `turn_unverifiable_fail_open`.

"I need to know it failed" stays AR-356's half: the pass-through records
receipts today, and the capsule disclosure line makes it visible in-turn.
Four pre-existing failures in `tests/test_coverage_final_host_cli.py`
reproduce identically on clean main (the AR-354 family) and are untouched
by this change.

## Dependencies

- AR-365 (the shared gate, now extracted and reused).

## Acceptance

- [x] A fail-open openclaw turn delivers the model's reply (with
      fail-open receipts recorded), never silence; pinned by a
      regression test at the node_bridge boundary.
- [x] Evaluated rejections on staffed turns keep their withhold
      semantics; a response racing preflight on a healthy turn is not
      granted a bypass (regression tests).
- [x] The gate implementation is shared with the hermes bridge, not a
      third copy (and now also covers the claude/codex/zcode Stop path).
- [ ] Live: an owner-visible openclaw fail-open turn delivers its reply
      on this installation.
