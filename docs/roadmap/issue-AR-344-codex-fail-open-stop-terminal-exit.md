---
title: "AR-344: Codex fail-open turn ends in Stop replay-mismatch and TUI exit"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [reliability, codex, hooks, fail-open, finalization]
related:
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/issue-AR-342-codex-activation-canary-route-unsatisfiable.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-344
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/399
depends_on: []
blocks: []
---

# AR-344: Codex fail-open turn ends in Stop replay-mismatch and TUI exit

## Problem

When a codex TUI turn's preflight fails open
(`workforce_inference_failed` / `inference_invalid`), the model's answer
is displayed (Rule 8 pass-through holds), but the Stop hook then prints:

    AGENCY TURN TERMINAL: The submitted response does not match the
    exact response accepted for this trace. It cannot be published or
    retried; begin a new user turn.

and the codex TUI **exits to the shell** ("To continue this session,
run `codex resume`"). A staffed turn in the same pane minutes later
(routing accepted 1.0, header rendered with the
`gpt-5.6-terra -> codex-review` route, specialists correlated in
`specialists_loaded`) closed cleanly and the TUI survived — so the exit
is specific to the fail-open + replay-mismatch path.

## Measured 2026-09-01 (runtime ec6c4b49 / launcher 23ebce86d6f4)

- Session `01a05d3c-…` 13:50:46→13:51:13Z: run `preflight_failed`,
  receipt `workforce_inference_failed ["inference_invalid"]`, correct
  answer displayed without header, Stop terminal message, TUI exited.
  Reproduced twice (also ~13:35Z under the mixed-binary window).
- Session `01a05d4b-…` 14:07:17→14:09:18Z: staffed turn, clean close,
  TUI alive. codex-cli 0.152.0 (single install, post AR-338 adoption).
- Caveat: both fail-open reproductions ran while the pinned codex binary
  was in (or near) its 0.151.0/0.152.0 mixed-file window; a clean
  0.152.0 fail-open reproduction is the first investigation step.

## Measured 2026-09-01 (Linux, clean codex-cli 0.152.0, runtime e5e2e193)

Reproduced deliberately by prompting a release-shaped request (the
deterministic fail-open trigger measured in AR-345): session
`01a05d64-…` turn `01a05d65-…` 14:35:20→14:36:09Z closed
`preflight_failed` with receipt `workforce_inference_failed
["inference_invalid"]` (four planner rejections, dominated by
`plan_missing_release_verification`), the prose answer displayed, and
the Stop hook printed the exact terminal replay-mismatch message — but
the **TUI survived** (prompt alive, no exit to shell). The Windows
exit-to-shell did **not** reproduce on a clean 0.152.0 Linux turn.

Stop hook I/O captured with a temporary launcher-bootstrap tee
(restored byte-identical afterward, hash-verified):

- stdin: full 0.152.0 Stop schema — `session_id`, `turn_id`,
  `transcript_path`, `cwd`, `hook_event_name`, `model`,
  `permission_mode`, `stop_hook_active`, `last_assistant_message`.
- stdout (exit 0): `{"continue":false,"stopReason":"AGENCY TURN
  TERMINAL: The submitted response does not match the exact response
  accepted for this trace. It cannot be published or retried; begin a
  new user turn."}`

## Answers

- **No "exact response accepted for this trace" exists.** `_handle_stop`
  (`agency_runtime/adapters/hooks.py:2861`) first looks for an exact
  terminal finalization; a fail-open turn has none because preflight
  already closed the run as `preflight_failed` without binding any
  response (`terminal_finalization_id` NULL). `_is_terminal_turn`
  (`hooks.py:3300`) then reports terminal for ANY run status outside
  `{active, evidence_only}` — conflating "lifecycle ended (by Agency's
  own preflight failure)" with "an exact response was bound". Every
  fail-open Stop submission therefore takes the mismatch branch; the
  message is unconditional, not a real digest comparison.
- **The stop directive is Agency-side; the exit is host-side.** The
  rejection is emitted with `retry=True`, which `_completion_rejection`
  (`hooks.py:241`) renders as `{"continue": false, "stopReason": …}` —
  a session-lifecycle stop, not the `{"decision": "block"}` response
  verdict. Linux codex 0.152.0 renders it as "Stop hook (stopped)" and
  keeps the TUI; the Windows exit saw the same payload, so the exit
  difference is codex-side handling (or the 0.151/0.152 mixed-binary
  window), not a different Agency instruction.
- **Fix direction:** a fail-open turn should take the Rule 8
  `_publish_unverified` path (or at minimum a `decision:block` shape)
  instead of the terminal-mismatch rejection — check the run's
  `preflight_failed`/fail-open status before treating a terminal
  lifecycle as a bound-response contract. Same conflation family as the
  hermes fail-open draft replacement (AR-346, which is worse: it
  replaces the answer).

## Acceptance

- [x] Reproduced (or ruled unreproducible) on a clean codex-cli 0.152.0
      fail-open turn, with the Stop hook's stdin/stdout captured.
      (2026-09-01 Linux: message reproduced and I/O captured; the TUI
      exit itself did not reproduce — remaining exit evidence must come
      from a Windows clean-0.152.0 turn.)
- [ ] Fail-open codex turns close without a terminal replay-mismatch,
      or the mismatch is shown to be codex-native behavior and
      documented; either way the TUI survives an inference hiccup.
- [ ] Regression coverage for the fail-open finalization path on codex.
