---
title: "AR-132: Hire deterministic safe staffing gaps"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [routing, workforce, hiring, contractors, inference]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - agency_runtime/core/selector/pipeline.py
  - agency_runtime/core/workforce/staffing_verifier.py
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-132
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-132: Hire deterministic safe staffing gaps

## Problem

The canonical uncovered-unit result includes `required_agents_missing`, but
the hiring eligibility helper rejects that reason. Multiple otherwise clean
gaps also disable hiring entirely, so configured values of
`max_hires_per_task` above one have no effect.

## Current state

A live installed route produced `required_agents_missing`,
`no_safe_sufficient_team`, and recruiter abstention with no hiring event.
Direct reproduction confirmed the helper returns no hireable unit for that
exact legitimate gap.

## Approach

Recognize only the exact safe no-team reason closure, process deterministic
clean gaps in stable order up to the configured cap, restaff after each hire,
and apply per-turn and daily budgets cumulatively. Persist created, declined,
budget-exhausted, and no-attempt outcomes in the routing receipt.

## Dependencies

This is a corrective slice of AR-119 and AR-122. AR-142 owns shared boundary
instrumentation.

## Acceptance

- A sole canonical safe gap hires, persists, restaffs, and can execute.
- Unrelated unsafe reasons never become hireable.
- Caps zero, one, two, and daily exhaustion behave distinctly and truthfully.
- Multiple clean gaps are handled in deterministic order up to the cap.
- Full-route tests cover inference nomination through durable hiring receipt.
