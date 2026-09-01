---
title: "AR-353: Intermittent staffing-verdict failures now measurable on the Linux box"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, inference, reliability, intermittent]
related:
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/issue-AR-335-make-content-invalid-completions-reach-fallback.md
  - docs/roadmap/issue-AR-352-scope-battery-deltas-by-session.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-353
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/417
depends_on: []
blocks: []
---

# AR-353: Intermittent staffing-verdict failures now measurable on the Linux box

## Problem

The AR-338 capsule documented an intermittent claude-route
staffing-verdict window on the Windows box since 2026-08-31 ~16:48Z
(`staffing_critic_rejected`, `inference_invalid`,
`selection_confidence_too_low` interleaved with confidence-1.0
acceptances) and instructed sessions not to chase it as a regression.
This record gives the signal a tracker and captures that the same
window is measurable on the Linux box through LiteLLM-backed routes,
where the Windows box uses per-harness CLI/API inference — pointing at
the shared inference stages, not a host's provider plumbing.

Measured 2026-09-01 on the Linux box (runtime at exact main
`7197ae11`, post-AR-345, planner stage healthy in every receipt):

- hermes release-shaped acceptance turn: attempt 1
  `staffing_critic_rejected`, attempt 2 staffed 4 specialists.
- hermes battery turns: recruiter-stage rejections
  (`recruiter_candidate_row_shape_invalid`,
  `recruiter_candidate_positive_evidence_invalid`, then a hard
  provider `failed`) at ~18:16Z and ~18:52Z; a pass at ~18:19Z;
  roughly half of hermes turns flapped across the deploy window.
- claude interactive sessions: `workforce_inference_failed
  ["inference_invalid"]` at 18:32-18:33Z and
  `staffing_critic_rejected` at 18:30Z interleaved with
  confidence-1.0 staffed turns (this session's own preflights).
- openclaw: cron turns failed at ~18:06Z; battery turns passed clean
  windows at ~17:59Z and ~18:47Z.

## Current state

Not chased as a regression per the AR-338 capsule; AR-345 removed the
deterministic planner-stage driver, so this window is now the dominant
source of fail-open turns. Fail-open turns still cost session
continuity on codex (AR-344) and answers on hermes (AR-346) until
those land.

## Approach

Instrument before theorizing: per-stage receipts already name the
failing stage (recruiter/critic dominate); correlate rejection bursts
with judge-stack load and provider latency, then decide whether the
fix is recruiter/critic prompt contracts, retry budgets, or provider
capacity. Coordinate with AR-335 (content-invalid completions should
reach the different-provider fallback).

## Dependencies

- AR-352 (clean battery measurement makes the window's rate visible).

## Acceptance

- [ ] The window's failure rate and dominant stage are measured over a
      bounded sample on both boxes.
- [ ] A root-cause disposition is recorded (contract, budget, capacity,
      or judge-stack), with the fix or an explicit accept-with-retry
      decision.
- [ ] Ordinary turns' staffing success rate returns to the pre-window
      norm (accepted turns no longer interleave with same-shaped
      rejections at the current rate).
