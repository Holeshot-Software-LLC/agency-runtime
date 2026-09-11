---
title: "Name the stale hook runtime when a turn cannot be verified"
status: accepted
category: decisions
created: 2026-09-11
updated: 2026-09-11
tags: [hooks, install, runtime-staleness, operations]
related:
  - docs/roadmap/issue-AR-440-a-stale-hook-runtime-blocks-every-turn-without-naming-itself.md
  - docs/decisions/0248-let-the-owner-opt-in-to-a-durable-dashboard-access-token.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0253
type: decision
deciders: [owner]
---

# ADR-0253: Name the stale hook runtime when a turn cannot be verified

## Status

**Accepted 2026-09-11.** Owner direction: a failure must name itself; a
block that cannot be diagnosed from what the operator sees is a defect.

## Context

A host session pins the hook launcher of the digest it loaded at start, on
purpose: the pin is what stops a mutable tree from redirecting hook code.
A reinstall publishes a new projection and a new configuration, and an
already-running session keeps calling the old launcher. When the new
configuration carries a key the old runtime's schema does not know, every
hook in the old session fails while opening the store, the Stop boundary
fails closed with the generic verification message, the prompt hook fails
open and records no run, and only a stderr line the host never shows names
the exception class. The owner's session met this on 2026-09-10 after the
AR-436 rollout and saw the same block on every turn for a day.

`runtime_staleness` already compares the running projection with the
per-host pointer the last install wrote, and the SessionStart hook reports
that drift once. A session that was running when the install happened never
receives SessionStart again.

## Decision

1. **A boundary failure consults the drift.** When a hook event fails at the
   boundary, the hook reads `runtime_staleness(host)`; the read is advisory,
   never chooses code, and is skipped on the ordinary path.
2. **A stale Stop names itself.** With drift, the Stop rejection reason
   states that this session's hooks run projection `<running>` while the
   host installed `<installed>`, that the failure class was `<class>`, and
   that restarting the session loads the installed hooks; the shape stays
   the retry form for claude and codex and the block form for zcode. Without
   drift the reason is unchanged. The reason carries digest prefixes, the
   host name and an exception class name, never a message body or a path.
3. **A stale prompt hook still publishes and says why.** The UserPromptSubmit
   boundary keeps failing open; its log entry and the stderr line carry the
   same drift beside the cause.
4. **The pin does not move.** No hook re-executes the installed launcher or
   reloads the configuration through another runtime; the fix is a named
   reason and a restart, not a fallback.

## Consequences

- An operator blocked by a stale session reads the cause and the remedy in
  the host, on the first blocked turn.
- A session whose runtime predates this decision cannot say so; the first
  session that can is one running this runtime when a later install lands.
- The drift read costs one bounded pointer read per failed event, plus the
  first import of the staleness module in that process (about 7 ms); the
  ordinary path pays nothing. Every event's stderr line names the drift on
  a boundary failure; host-visible results change only for Stop.
- The reason states the drift beside the failure class; it does not assert
  that the drift caused the failure.
