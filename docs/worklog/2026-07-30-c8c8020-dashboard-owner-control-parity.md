---
title: "Worklog detail: fix(dashboard): restore owner control parity"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [dashboard, authority, configuration, controls, security]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c8c8020e43f565392fa63dfab46e2c6a4a4c0a51
short: c8c8020
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: fix(dashboard): restore owner control parity

## Purpose

Make the installed dashboard the owner configuration and control surface
advertised by the README while preserving the read-only broker boundary.

## Approach

Owner-authenticated POST requests now reach the existing bounded dashboard
mutation handlers. An exact broker bearer is rejected with `403 owner control
required` before dispatch, while unrecognized credentials remain unauthorized.
The packaged client restores configuration, retention, master, host, roster,
workforce, and hiring controls with their typed confirmations and revision or
generation bindings.

The client merge retained newer request correlation, stale-response rejection,
lifecycle cancellation, bounded collection rendering, activation disclosure,
and stale-Store interlocks. The HTML shell was restored byte-for-byte from the
last owner-capable pre-regression Git blob rather than reconstructed from a
displayed or transformed copy.

## Challenges encountered

The read-only regression spanned server authorization, client action exports,
event wiring, rendered controls, master-state synchronization, configuration
dirty-state logic, and static shell assertions. The first shell recovery attempt
revealed that tool-displayed large output can be truncated; that uncommitted
copy was discarded and replaced from bounded Git chunks, with the resulting
blob hash verified exactly before testing.

## Decisions and alternatives

ADR-0117 governs the owner authority boundary. The owner bearer is equivalent
to normal owner CLI authority; the broker, hook, and MCP credentials are not.
Removing dashboard authentication was rejected: automatic loopback bearer
isolation, Host and Origin checks, and token scrubbing remain in force.

## Verification

- `node --test tests/dashboard_ui.test.mjs`: 110 passed, including exact
  request bodies for all eight owner mutation endpoints.
- Dashboard authentication and server tests: 145 passed, 3 platform skips.
- Focused Ruff, format, documentation metadata, and whitespace checks passed at
  the checkpoint boundary.
- Context telemetry reported 10.7 percent remaining, requiring this clean
  checkpoint before inference-only staffing work.

## Follow-ups

Remove deterministic specialist, team, and hiring decisions from substantive
routing while keeping deterministic recall, eligibility, and validation.
