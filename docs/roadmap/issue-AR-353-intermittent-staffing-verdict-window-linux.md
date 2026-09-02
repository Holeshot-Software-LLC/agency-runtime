---
title: "AR-353: Intermittent staffing-verdict failures now measurable on the Linux box"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
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

## Measurement (2026-09-02, Linux box)

`agency evidence staffing` (this change) reads the store's turn counts and
newest failure receipts since a canonical cutoff and projects rates,
dominant stages, and reason codes per host — counts over closed
vocabularies only. Measured on this installation at 2026-09-02 ~04:40Z
(runtime deployed at main `6ba65aa9`, LiteLLM-backed routes):

| window | host | turns | preflight_failed | rate | failing stage | dominant staffing code |
|---|---|---|---|---|---|---|
| 24 h | claude | 71 | 45 | 63.4% | recruiter ×22, critic-after-applied ×13, planner ×5 | staffing_critic_rejected ×18, inference_invalid ×17 |
| 24 h | codex | 149 | 119 | 79.9% | recruiter ×61, planner ×45 | selection_confidence_too_low ×37, inference_invalid ×36, staffing_critic_rejected ×36 |
| 24 h | hermes | 30 | 16 | 53.3% | planner ×9, recruiter ×6 | inference_invalid ×11 |
| 24 h | openclaw | 19 | 9 | 47.4% | planner ×4, recruiter ×4 | inference_invalid ×7 |
| 24 h | all | 273 | 189 | 69.2% | recruiter (dominant provider outcome `recruiter rejected/provider_response_contract_invalid`) | — |
| 6 h | all | 45 | 38 | 84.4% | recruiter ×19 | inference_invalid ×11, staffing_critic_rejected ×11 |

Per-stage provider outcomes over the 24 h receipts: recruiter `rejected /
provider_response_contract_invalid` ×475 against `applied` ×79 and `failed /
provider_no_valid_response` ×17; planner `applied` ×178, `failed` ×50,
`rejected` ×48; reranker `rejected` ×22; critic `applied` ×64 (every
critic call applied — the critic's *verdict* is the rejection). Recruiter
validation codes: `staff_without_safe_team` ×408, `invalid_candidate`
×166, `recruiter_candidate_positive_evidence_invalid` ×41,
`recruiter_candidate_row_shape_invalid` ×31; planner
`plan_missing_release_verification` ×36, `plan_missing_implementation`
×15. Receipts carry no per-attempt timing, so provider latency cannot be
correlated from them (`routing_decisions.latency_ms` covers successful
routes only; `agency evidence latency`).

First root-cause disposition from the data alone: the dominant shape is
the recruiter returning well-formed JSON that fails Agency's own
validation contract — `staff_without_safe_team` (the recruiter names a
team the safety/sufficiency rules refuse) and `invalid_candidate` (a slug
the roster does not carry) — not a provider outage. That points at the
recruiter prompt/contract pair and the safe-team rule, with the strict
critic as the second gate (`verdict_after_applied_attempts` ×13 on
claude). The Windows box is not measurable from here; its half of the
first box stays open.

## Dependencies

- AR-352 (clean battery measurement makes the window's rate visible).

## Acceptance

- [ ] The window's failure rate and dominant stage are measured over a
      bounded sample on both boxes — Linux measured above with
      `agency evidence staffing` (24 h: 273 turns, 69.2% fail-open, recruiter
      dominant); the Windows box is still unmeasured.
- [ ] A root-cause disposition is recorded (contract, budget, capacity,
      or judge-stack), with the fix or an explicit accept-with-retry
      decision.
- [ ] Ordinary turns' staffing success rate returns to the pre-window
      norm (accepted turns no longer interleave with same-shaped
      rejections at the current rate).
