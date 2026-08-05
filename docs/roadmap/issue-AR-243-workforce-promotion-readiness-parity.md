---
title: "AR-243: Workforce promotion readiness parity (sub-issue 2 of AR-236)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, workforce, promotion, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
  - agency_runtime/cli/workforce_commands.py
  - agency_runtime/dashboard/dashboard-render.js
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-243
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/252"
depends_on: []
blocks: []
---

# AR-243: Workforce promotion readiness parity (sub-issue 2 of AR-236)

## Problem

The dashboard's worker detail panel renders a rich "Promotion readiness"
card (`dashboard-render.js:1450-1466`) with `verified_successes`,
`required_successes`, `remaining_successes`, `eligible_for_automatic_promotion`,
`in_review_window`, `reasons`, and `evidence_rule`. The CLI's
`workforce show` text mode only prints `verified`, `required`, and a binary
`automatic=ready|not-ready` — omitting the review-window state, remaining
count, reasons, and evidence rule.

## Current state

- The CLI's `cmd_workforce_show` calls `promotion_readiness` (which now
  returns the full field set including `in_review_window` from AR-242) but
  only prints three fields in text mode.
- The dashboard renders the full card from the same `promotion_readiness`
  projection.

## Approach

Update the CLI `workforce show` text mode to print the same promotion
readiness fields the dashboard renders:

- `verified`, `required`, `remaining`, and `automatic` state (including
  `review-window` when the contractor is within the window).
- `review-window\tactive` when the window is active.
- Each reason from `reasons[]`.
- The `evidence_rule`.

## Acceptance

- [ ] The CLI `workforce show` text mode prints `verified`, `required`,
      `remaining`, `automatic`, review-window state, reasons, and
      evidence rule — matching the dashboard's promotion readiness card.
- [ ] JSON mode is unchanged (already emits the full projection).
