---
title: "AR-341: Deliver Agency capsules to hermes interactive gateway sessions"
status: open
category: roadmap
created: 2026-08-31
updated: 2026-08-31
tags: [reliability, hermes, delivery, finalization]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-341
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/386
depends_on: []
blocks: []
---

# AR-341: Deliver Agency capsules to hermes interactive gateway sessions

## Problem

Interactive hermes gateway TUI turns staff successfully but never receive
the Agency capsule, and turn-scoped finalization then blocks every
interactive draft. The host is effectively unusable interactively while
Agency is on: each completed response is replaced with "Agency Runtime
blocked an unverified draft because turn-scoped finalization did not
accept it. Restore correlation and evidence, then start a new turn."

The headless path is healthy: `hermes -z <task>` (the harness battery's
ordinary drill) receives injection, staffs, and finalizes, so the defect
is specific to how capsule delivery reaches long-lived gateway chat
sessions rather than launcher-wrapped one-shot processes.

## Measured 2026-08-31

All on Hermes Agent v0.21.0 (upstream 5505042f), gateway
`hermes-gateway-nexus` restarted after the projection republish, runtime
venv at f91541c3, inference operational, roster fix #382 live:

- Work-shaped interactive turn ("review the configuration loader error
  handling") at 21:29:50Z: `routing_decisions` row `accepted` /
  `computed` with `["codebase-onboarding-engineer", "code-reviewer"]` —
  staffing succeeded.
- The model's own probe inside the same turn found
  `HERMES_CONTEXT_HEADERS` empty and no capsule text in context; it
  answered HEADER-ABSENT while producing a correct substantive review.
- Finalization then replaced the streamed response with the blocked-draft
  message. Reproduced on three interactive turns (fresh client, fresh
  `/new` session, fresh gateway).
- Battery receipt the same hour: `hermes: passed` with staffed rows —
  headless injection works.
- Ruled out (same evening): the full discovery `agency install` registered
  the native gateway plugin at
  `~/.hermes-nexus/plugins/agency-preflight/` and `hermes plugins list`
  shows it `enabled` (0.1.0, user source); the gateway was restarted
  after the registration (plugin mtime 21:58:55Z, gateway
  ActiveEnter 22:11:22Z) and imported it (`__pycache__` present).
  A fresh client turn after all of that still staffed, received nothing
  (`HERMES_CONTEXT_HEADERS` empty, HEADER-ABSENT), and was blocked at
  finalization — so registration and loading are not the missing piece;
  the defect is inside the plugin's interactive-session delivery or the
  finalization correlation for gateway chat turns.

## Resolution (2026-08-31) — delivery fixed, one residual

Root cause: hermes bounds ``pre_llm_call`` (with the other agent-turn
hooks) by ``plugins.hook_callback_timeout`` — default 30s — and abandons
the callback on timeout without joining it. The rendered bridge takes
17–72s to staff a turn on this box, so every interactive staffing hook
was abandoned: the orphaned worker still recorded accepted routing while
the capsule never reached the session. ``~/.hermes-nexus/logs/errors.log``
shows ``Hook 'pre_llm_call' callback _pre_llm_call timed out after 30s —
skipping`` on every interactive turn, ending the moment the budget was
raised; the next turn's first API call grew from ~13K to 25,830 input
tokens, and the model then quoted the injected ``[Agency
resident-steward kernel v4]`` header verbatim from its context.

Fix (PR #390, deployed): hermes registration reads the deployed plugin's
own ``_TIMEOUT_SECONDS`` (ceiling 600) and ensures
``plugins.hook_callback_timeout`` covers it plus a 5s margin via the
hermes config CLI (600 live), recording ``hook_budget_read`` /
``hook_budget_write`` evidence steps and failing loudly when the write
is refused.

Residual (the only unmet acceptance item): finalization still blocks a
draft whose header block is complete and correct but preceded by a
preamble sentence — observed live with the full five-line header plus
Why/How and the actually-staffed specialists, rejected solely for not
being first. That is header-contract compliance of the local
``qwen3-coder-30b`` chat model against the exact-start rule, not
delivery; remediation is a stronger interactive model (``hermes model``)
or a deliberate finalization-policy decision, tracked here.

## Expected

An interactive hermes turn that staffs successfully must receive the same
capsule/header material as a headless turn, and a turn that Agency itself
staffed must be finalizable. If delivery to a session is impossible, Rule
8 pass-through should apply rather than blocking the host's response.

## Acceptance

- A work-shaped prompt in a live hermes gateway TUI session quotes its
  injected Agency header and finalizes (no blocked-draft replacement).
- `agency battery --host hermes --force` still passes.
- Evidence rows show capsule delivery bound to the interactive session's
  trace, not only to `-z` invocations.
