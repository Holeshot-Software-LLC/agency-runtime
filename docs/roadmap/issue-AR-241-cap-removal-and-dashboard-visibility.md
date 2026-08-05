---
title: "AR-241: Hiring cap removal and dashboard visibility (slice 5 of AR-235)"
status: open
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [workforce, hiring, observability, sub-issue]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/selector/pipeline.py
  - agency_runtime/core/config_defaults.yaml
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-241
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/250"
depends_on: []
blocks: []
---

# AR-241: Hiring cap removal and dashboard visibility (slice 5 of AR-235)

## Problem

AR-235 §5 removes `max_hires_per_task: 1` and `max_hires_per_day: 3` as
hard caps. They cause silent incompleteness with no operator visibility.
The intent (prevent runaway, prevent stretch-into-generalist) is right
but the enforcement is wrong: a hard cap hides the failure mode instead
of instrumenting it. The amend-first default (AR-240) is the actual guard
against runaway.

## Current state

- `max_hires_per_task: 1` rejects hiring when
  `workforce_changes >= max_hires_per_task` in the selector pipeline
  (`pipeline.py:1255, 1337`) and in `hire_contractor_for_gap`
  (`hiring.py:1799`).
- `max_hires_per_day: 3` rejects hiring when
  `_today_hires(store) >= max_hires_per_day` (`hiring.py:1847, 820,
  2073`). The daily cap is checked at hire time and re-checked at commit.
- `max_selected_total: 16` bounds the total selected workers per turn
  (`config_defaults.yaml`).

## Approach

Replace the two hard caps with soft bounds:

- `max_hires_per_turn: 16` (matches `max_selected_total`). This bounds
  how many hires can happen in one turn without rejecting.
- `daily_hire_alert_threshold: 50` — a soft warning threshold. When the
  daily cumulative exceeds this, the case ledger records a warning flag;
  no rejection.
- Remove the `max_hires_per_task < 1` early abstain in
  `hire_contractor_for_gap`.
- Remove the `max_hires_per_day` rejection checks in the hiring path and
  commit path. The per-day cumulative is still recorded for dashboard
  visibility.
- The case ledger records the per-turn hire count and per-day cumulative
  so the dashboard can chart them.

The cap is a hint, not a wall. The amend-first default is the actual
guard against runaway.

## Dependencies

- AR-240 (amend-first) — done; the amend-first default is the guard.

## Acceptance

- [ ] `max_hires_per_task` and `max_hires_per_day` no longer reject
      hiring in the runtime path.
- [ ] `max_hires_per_turn: 16` and `daily_hire_alert_threshold: 50` are
      added as soft bounds.
- [ ] The daily cumulative is still recorded for dashboard visibility.
- [ ] Focused tests cover: cap removal (no rejection), soft-warning
      behavior.
