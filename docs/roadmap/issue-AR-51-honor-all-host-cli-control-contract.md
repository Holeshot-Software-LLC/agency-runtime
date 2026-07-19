---
title: "AR-51: Honor the all-host CLI control contract"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [cli, host-integrations, runtime-control, usability, contract]
related:
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-51
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/52
depends_on: []
blocks: [AR-57]
---

# AR-51: Honor the all-host CLI control contract

## Problem

The `agency on` and `agency off` help text says that omitting `--agent` targets
every detected host. The implementation instead succeeds only when exactly one
host is detected and asks the operator to select a host when multiple hosts are
present.

## Current state

Explicit single-host control and omitted-`--agent` all-host control share one
deterministic implementation. The short command targets only hosts proven by
current native inventory, emits one ordered result per host in text and JSON,
preserves successful results when another host fails, and returns nonzero for
any partial failure. Native lifecycle remains an explicit separate option.

## Approach

Resolve an omitted host argument to the complete deterministic detected-host
set. Apply the requested control to every member, report one result per host,
and return failure when any member fails while preserving all successful
results. Keep explicit `--agent` behavior and the empty-detection diagnostic.

## Dependencies

This builds on the persistent soft-control and reversible native lifecycle
contracts established by ADR-0010 and ADR-0034.

## Acceptance

- [x] Omitting `--agent` applies `on` or `off` to every detected host.
- [x] Multi-host output is deterministic in text and JSON modes.
- [x] Partial failures return nonzero and identify every per-host result.
- [x] Explicit single-host and no-host behavior remain compatible.
- [x] Full exact-coverage, Windows/Linux, CLI, and tracker gates pass.
