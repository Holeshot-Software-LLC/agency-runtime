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

## Questions to answer

- Why does the finalization verifier report a replay mismatch on a
  fail-open turn at all — what "exact response accepted for this trace"
  exists when no staffed contract was bound? Suspect the terminal-trace
  replay contract binding a response fingerprint that the fail-open
  path never recorded, making every submission mismatch.
- Is the TUI exit codex's own reaction to the hook's Stop decision
  (decision payload shape?) or an Agency-side instruction? The exit
  costs session continuity on every inference hiccup, which under an
  intermittent inference window (see the AR-338 capsule's 2026-09-01
  findings) means frequent forced restarts.

## Acceptance

- [ ] Reproduced (or ruled unreproducible) on a clean codex-cli 0.152.0
      fail-open turn, with the Stop hook's stdin/stdout captured.
- [ ] Fail-open codex turns close without a terminal replay-mismatch,
      or the mismatch is shown to be codex-native behavior and
      documented; either way the TUI survives an inference hiccup.
- [ ] Regression coverage for the fail-open finalization path on codex.
