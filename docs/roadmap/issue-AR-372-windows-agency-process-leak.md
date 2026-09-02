---
title: "AR-372: Windows accumulates live agency MCP/CLI processes until spawning fails"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [windows, process-lifecycle, mcp, install, resource-exhaustion]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-369-stale-host-process-serves-a-superseded-kernel.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-372
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/526
depends_on: []
blocks: []
---

# AR-372: Windows accumulates live agency MCP/CLI processes until spawning fails

## Problem

Operator report, 2026-09-02, Windows host running codex:

- the machine reached **98.6% commit charge**;
- roughly **2,100 live agency-cli / MCP node processes**, all with **live
  parents**;
- process creation failed as a result, which is what broke `git` spawning;
- observed while re-running the suite alone, with no other load.

Live parents is the important detail. These are not orphans that lost their
supervisor: something is spawning children per turn or per tool call, holding
them, and never reaping them. At roughly 2,100 processes the failure is not a
slow leak either — it is fast enough to exhaust a workstation inside one
suite run.

This is filed p0 because the failure mode is the operator's machine, not a
turn: once process creation fails, everything on the box fails, including the
tools needed to diagnose it.

## Reproduced (2026-09-02)

The leak is not Windows-specific and not the host's: it reproduced on the
maintainer's Linux box, in Agency's own process. Two
`agency_runtime.server.mcp --stdio` processes were alive **16h13m** and
**15h28m**, each still parented by a running host session, each pinned to a
launcher tree two deploys old, each asleep on a stdin socket nobody would
write to again.

The operator's Windows census showed the same pairing -- Agency launcher
processes under a live `claude.exe`, plus one adopted by `svchost.exe` after
losing its parent.

Mechanism: the stdio server exits correctly when stdin closes (verified,
`rc=0`, and hook processes exit in 0.3-1.3s). It has no answer for a client
that **keeps the pipe open and stops talking**, which leaks one server per
abandoned session. At a suite run's spawn rate that reaches thousands.

Both bounds were needed. Parent liveness alone would not have caught the
measured leaks, because their parents were alive -- long-running sessions
that had simply stopped using their server.

## Current state

Not yet reproduced by the maintainer — this box is Linux, and the report is
Windows-specific. What is known about the spawn surfaces Agency owns:

- Agency registers one MCP server per host through `.mcp.json`, launched as
  `agency_runtime.server.mcp --stdio` (`installer_payloads.mcp_servers`).
  That server is a Python process; the reported processes are node, so the
  node parents are most likely host-side MCP clients or the codex CLI, with
  Agency's server as their child.
- The codex hook contract fires eight events per turn, each spawning a
  process (`installer_payloads.codex_hooks`).
- `agency_runtime/core/owned_process_windows_atomic.py` exists precisely to
  create Windows children inside a Job Object so they cannot outlive their
  owner. Any spawn path that does **not** go through it has no such
  guarantee, which makes "which spawn paths are Job-Object-owned on Windows"
  the first question to answer.

## Approach

1. Reproduce with a bounded process census on Windows: count live agency
   processes per turn across a suite run, recording parent PIDs, so the
   spawning site is identified from evidence rather than inferred.
2. Establish whether every Windows spawn path Agency owns creates its child
   inside a Job Object, and close any that does not.
3. Bound it regardless of the source: Agency should refuse to spawn beyond a
   ceiling of live owned children, and report that refusal, rather than
   participating in exhausting the machine.

## Dependencies

- None. This is independent of the staffing and header work.

## Implementation (2026-09-02), step 1

`agency_runtime/core/stdio_lifetime.py` gives the stdio server a bounded
lifetime, and `run_stdio` starts it. Two independent bounds, both advisory
and fail-open -- a bound that cannot be evaluated never ends a server:

- **Idle timeout**, default 4 hours, operator-overridable within 60s..24h via
  `AGENCY_MCP_IDLE_TIMEOUT_SECONDS`. Deliberately far above any real gap
  between turns, because a server is bound to one session and ending it early
  would break the next tool call in a session the user still holds open.
- **Parent liveness**, asserted only on POSIX, where an orphan is reparented
  so a changed ppid is proof. Windows does not reparent and reuses process
  ids, so a pid comparison there can answer about a stranger; it declines to
  answer and leaves the work to the idle bound.

Verified end to end against the measured shape: a server whose client holds
the pipe open and never speaks exits at the bound with `rc=0` and
`agency mcp server exiting: idle_timeout` on stderr. Closing stdin still
exits immediately.

Steps 2 and 3 (auditing every Windows spawn path for Job Object ownership,
and a ceiling on live owned children) remain open.

## Acceptance

- [x] A stdio server whose client keeps the pipe open and stops talking ends
      itself rather than sleeping forever. Evidence:
      `agency_runtime/core/stdio_lifetime.py`, its `run_stdio` wiring, and
      `tests/test_stdio_lifetime.py` (13 tests, including that a slow client
      is never ended and that an unevaluable parent check never ends one).
- [ ] A suite run on Windows leaves no growing population of live agency
      processes; the count returns to its pre-run baseline.
- [ ] Every Windows spawn path Agency owns creates its child inside a Job
      Object, pinned by a test.
- [ ] Exceeding a bounded number of live owned children is refused and
      reported, so Agency cannot contribute to machine-wide exhaustion.
