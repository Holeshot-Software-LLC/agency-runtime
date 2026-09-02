---
title: "AR-372: Windows accumulates live agency MCP/CLI processes until spawning fails"
status: open
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

## Acceptance

- [ ] A suite run on Windows leaves no growing population of live agency
      processes; the count returns to its pre-run baseline.
- [ ] Every Windows spawn path Agency owns creates its child inside a Job
      Object, pinned by a test.
- [ ] Exceeding a bounded number of live owned children is refused and
      reported, so Agency cannot contribute to machine-wide exhaustion.
