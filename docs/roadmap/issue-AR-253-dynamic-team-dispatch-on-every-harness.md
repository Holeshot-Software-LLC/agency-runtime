---
title: "AR-253: Prove staffing latency, rate, and cross-host parity"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-12
tags: [workforce, staffing, latency, harnesses, eval, host-evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/adapters/hooks.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-253
priority: p0
tracker_url: null
depends_on: [AR-180, AR-252, AR-255]
blocks: [AR-119]
---

# AR-253: Prove staffing latency, rate, and cross-host parity

## Problem

The prior issue described per-plan-row Job B dispatch, which has been retired.
The live remaining product contract is narrower and harder: measure whether
inference staffs host-spawned children, how long the decision and delivery take,
whether every supported host writes proof of multiple delivered cards, and
whether accepted outcomes drive the same automatic-promotion behavior.

Current computed routing is far outside the pinned 15,000 ms cold budget: the
AR-119 evidence reports roughly 2.4 provider calls per decision, p50 88.3 s,
and p95 195.9 s. Claude has three positive prior-candidate Rule-4 artifacts;
Codex has prior-candidate negative observations across TUI, Desktop, and exec
and a current source negative. Neither host has exact-candidate installed/live
proof; ZCode, Hermes, and OpenClaw are unproven.

## Current state

`agency evidence latency` exposes overall and decision-source distributions,
but there is no fixed staffing-rate harness that joins selection, host spawn,
card delivery, and per-stage latency. Existing Agency Store rows cannot stand
in for host-written delivery proof.

## Approach

Add `agency eval staffing` over a versioned ask set. Report valid-decision,
staffed-child, multi-card host-proven-delivery, accepted-outcome, promotion, and
failure rates plus provider, validation, delivery, and end-to-end latency.
Preserve the one-call fast path and reuse one inference-owned parent decision
for children; optimize prompts, stage routing, cache identity, and bounded
repair without weakening ADR-0118 or evidence gates.

"One staffing call" means one successful recruiter/staffing decision after any
separate intent-planning stage; it does not silently supersede ADR-0132's bounded
planner and recruiter repair allowances. Report all stage attempts and latency.

Prove Claude and Codex locally, then ZCode, Hermes, and OpenClaw on installed
hosts. Unavailable hosts remain explicitly unproven.

## Dependencies

- AR-255 owns inference and evidence authority.
- AR-180 owns the Codex live canary after that authority is repaired.
- AR-252 owns the accepted-outcome and automatic-promotion implementation that
  this issue proves across every host.
- AR-125 owns the separate matched Agency-on/off value claim.

## Acceptance

- [ ] `agency eval staffing` emits a machine-readable manifest with fixed asks,
      candidate identity, stage timings, decision validity, selected cards, and
      host-artifact correlation.
- [ ] The configured path uses no more than one successful recruiter/staffing
      decision per turn and meets the unchanged 15,000 ms cold budget.
- [ ] At least 95% of valid selection-requiring fixed-set asks are staffed and delivered; invalid,
      timed-out, or malformed provider arms are reported, never scored as
      staffing losses.
- [ ] On Claude, Codex, ZCode, Hermes, and OpenClaw, at least one host-spawned
      child has a current host-written proof of two or more compatible,
      inference-selected cards before first speech. One child with one card is
      not Rule-4 completion.
- [ ] Every supported host independently admits at least one host-evidenced
      producer outcome plus a distinct inference-selected verifier's bound
      verdict into the same normalized accepted-outcome contract.
- [ ] The host-agnostic promotion core has no host-specific branch and promotes
      an eligible contractor after any three distinct normalized accepted
      outcomes, including a mixed-host case, with no operator action.
- [ ] An unavailable supported host remains visibly unproven and cannot satisfy
      this issue or AR-119 closure.
- [ ] Optimization introduces no deterministic specialist choice, evidence
      downgrade, conversational hard block, or unsupported superiority claim.
