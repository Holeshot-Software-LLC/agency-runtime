---
title: "AR-349: Repair-budget exhaustion persists no rejected hiring case"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, hiring, audit-trail, evidence]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-349
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/407
depends_on: []
blocks: []
---

# AR-349: Repair-budget exhaustion persists no rejected hiring case

## Problem

When the hiring safety-repair loop exhausts its budget
(`agency_runtime/core/workforce/hiring.py:1201-1206`), the outcome is
`rejected` only in the in-memory `ContractorHiringOutcome`; no hiring
case row with `status = rejected` is written
(`tests/test_workforce_dynamic_hiring.py` asserts
`outcome.hiring_case is None`). AR-235's audit-trail contract ("the
case → rejected ... recorded in the audit trail") has no durable
record: an operator cannot later see that a contractor was proposed,
reviewed unsafe three times, and refused.

## Current state

Found by the AR-347 per-criterion audit of AR-235 (2026-09-01).
Per-attempt model receipts are persisted, but the rejection verdict and
attempts array exist only in memory; the dashboard cannot render a
rejection trail (AR-235 item 10/11 territory).

## Approach

Persist a `rejected` hiring case on budget exhaustion carrying the
per-attempt verdict history (the shape `_safety_repair_loop` already
holds), keep the fail-open-to-generalist behavior unchanged, and update
the exhaustion test to assert the durable row instead of `None`.

## Dependencies

None; the AR-235 dashboard plane can later render what this persists.

## Acceptance

- [ ] Budget-exhausted hires write one hiring case with
      `status = rejected` and the per-attempt verdicts, without
      instantiating a worker.
- [ ] The affected work unit still fails open to a generalist with
      `Recruited via: none`.
- [ ] Focused regression coverage on the persisted rejection.
