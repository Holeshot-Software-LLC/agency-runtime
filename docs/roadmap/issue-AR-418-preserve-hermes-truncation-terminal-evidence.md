---
title: "AR-418: Preserve Hermes truncation failure and terminal evidence"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [hermes, lifecycle, failure, finalization]
related:
  - docs/decisions/0016-central-finalization-and-session-correlation.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-08-hermes-openclaw-native-refresh.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-418
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/796
depends_on: []
blocks: []
---

# AR-418: Preserve Hermes truncation failure and terminal evidence

## Problem

A fresh normal Hermes turn accepts staffing and receives the selected specialist
card, then prints `Response truncated due to output length limit`. The CLI exits0,
without a truthful five-line header or accepted finalization; Agency remains active.
Exit status and installation success therefore conceal an incomplete native turn.

## Current state

A concrete native candidate is preserved in
`evidence/AR-418-hermes-native-terminal.patch` (native commit59e52e556a on
base7cd91114b4). The two real conversation-loop regressions fail on the unchanged
base with missing failed state and pass with the patch. Native34tests pass:
truncation failure diagnostics use a dedicated transform, emit session-end failure,
and printable partial results exit nonzero. Agency now consumes that optional
hook, derives failure headers from exact current Store correlation, and closes
failed runs without accepting partial output. Missing/cross-session traces retain
pass-through diagnostics and cannot close another turn. Adapter94tests pass.
The native candidate is not installed or merged upstream; installed ordinary
Hermes success and exact original provider branch remain unproven. No old failed
receipt has been finalized. This is a candidate, not AR-418 acceptance.


September 8 continuation source inspection confirms that native
`agent/conversation_loop.py` returns early both for length exhaustion and for
malformed tool-call JSON classified as truncated. These paths bypass
`agent/turn_finalizer.py`, including output transformation and `on_session_end`.
The outer native runner classifies a result without `failed=true` as relay
success even when `completed=false` and `partial=true`; the one-shot CLI also
returns zero when partial failure has printable text. Existing supported plugin
hooks expose no terminal-result transformation for those early returns. A repair
must cover that native boundary; merely adding adapter cleanup cannot establish
the original acceptance criteria. The original failed receipt remains unchanged,
and its exact branch/provider cause is still unproven.

Session20260908_155517_dc98fe, trace
20260908_155517_dc98fe:8671381b-3125-48ae-98a4-29c8f43c4209:1c4ea053.
Installed source8629e2ed with refreshed Hermes projection6e7dc299c23e. Staffing
accepted code-reviewer in146.452s. Full card is in native model-facing api_content.
The first native model receipt identifies glm-5.2 via alias-hermes-chat. A terminal
inline Python example and finalizer tool search completed; finalizer was not called.
Total340.061s, exit0, native usage completed=false, no terminal Agency event.
Exact bounded evidence is retained in evidence/AR-404-hermes-native-20260908.json.

Installed Hermes source inspection finds output-limit early returns that bypass
normal finalize_turn. The raw second provider response, exact return branch and
actual token cap are not captured; the error literal alone does not prove them.
This differs from AR-346's preflight-failure transform and AR-280's post-response
internal call: this turn staffed successfully and never finalized a response.

## Approach

Trace the native output-limit return and lifecycle callback using supported,
turn-bound evidence. Preserve terminal failure and truthful diagnostic delivery
without accepting partial output or guessing response/correlation. Determine
whether the native host must expose the failure callback before an adapter can
safely consume it. Do not change staffing, critic policy or output budgets merely
to obtain an accepted trial. Keep the original failed receipt immutable.

## Dependencies

Hermes native failure lifecycle and ADR-0016 central finalization/correlation.
AR-404 records the current installed native observation.

## Acceptance

- [ ] The exact native truncation failure is reproduced and its provider/host
      boundary is identified without inferring a token cap from the error text.
- [ ] A failed native turn records truthful terminal failure and diagnostic
      headers without accepting the truncated response or leaving false success.
- [ ] Missing and cross-turn correlation remain rejected, and ordinary accepted
      finalization still works with unchanged staffing and critic gates.
- [ ] Focused checks and fresh installed native evidence establish the repair;
      repository, tracker and exact worklog records agree.
