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

## Where the latency actually is (measured 2026-08-14, `9e29aabe`)

The budget overrun is **the recruiter stage**, not process overhead. Measured on
one live Windows workstation against the real `claude-subscription` CLI
transport:

| what | measured |
|---|---|
| `claude -p` process cost under the transport's own isolated environment | 8.3 s warm, 9.2 s cold |
| planner call, end to end | 15.9 s |
| recruiter call, end to end | 59.3 s and 94.0 s |
| one accepted in-path turn (hook surface, 5 specialists, confidence 1.0) | 106.3 s |

Subtracting the ~9 s process floor, the planner spends ~7 s on inference and the
recruiter **50-85 s**, so the recruiter is roughly 7-12x the planner and owns the
overrun. A fresh isolated home costs no more than a reused one (9.2 s vs 8.3 s),
so pooling or warming the transport's home directory is not the lever.

Two measurement traps were found in the process, both of which inflate numbers
that look like product latency:

1. **A direct `claude` CLI run while a Claude session is open stalls exactly
   60 s** on `~/.claude.json` lock contention — the debug log says
   `Lock acquisition took longer than expected - another Claude instance may be
   running`. The same invocation costs 83-95 s with the lock and 8-9 s without.
   **Agency's transport is not affected**: `_isolated_invocation_environment` in
   `agency_runtime/core/cli_transport.py` redirects `HOME`/`USERPROFILE`/
   `APPDATA` to a private directory while keeping `CLAUDE_CONFIG_DIR` real, which
   preserves authentication and sidesteps the lock. Do not attribute this 60 s to
   Agency.
2. `agency route` from the CLI runs on an unproven surface and rejects 251 of 282
   candidates as `execution_host_unproven`, so its latency and its
   `staff_without_safe_team` failures are both artifacts. Measure staffing from
   `routing_decisions` rows produced by the hook path.

The earlier p50 88.3 s / p95 195.9 s figures are therefore plausible as real
inference cost rather than startup overhead, and the remeasurement should target
the recruiter prompt — 282 candidates per call — before anything else.

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

## The recruiter rejection is a plan defect wearing a recruiter's name (2026-08-15)

With the runtime repaired, the live Claude canary reaches routing and dies at
`workforce_inference_failed` / `inference_invalid`. The receipt now explains
itself: both recruiter attempts on sonnet were rejected
`provider_response_contract_invalid` with one identical validation failure,
`staff_without_safe_team` on `unit-python-strip-regression-review`, and
`eligibility_reason_codes` empty.

`staff_without_safe_team` fires in `_validate_nomination_decisions` when the
recruiter decided `staff` but `proposal_row.selected` came back empty — that is,
no team within `max_selected_per_unit` (4 here) covers `_requirements(unit)`.
Coverage is conjunctive across six axes: `artifact`, `lifecycle`, `domain`,
`stack`, `capability`, `authority`. **If any one axis is uncoverable by the
whole roster, no ranking the recruiter could return would help.**

Measured offline against the live 283-contract roster, no inference involved:

- A realistic review unit (`review-report` / `review` / `software-engineering` /
  `python` / `review` / `review`) **is** staffable.
- Sweeping every roster-declared value one axis at a time: **0 of 8 lifecycles,
  0 of 8 artifact kinds and 0 of 4 authorities are unstaffable.** The typed
  space is healthy.
- A single off-vocabulary value is fatal and permanent: `lifecycle:verification`,
  `artifact:code-review`, `domain:code-review` each leave exactly that
  requirement uncoverable.

So the question is what the planner is allowed to emit. Two gaps, and only two:

1. **`lifecycle_phase: coordination` is enum-legal and declared by zero
   contracts.** `_LIFECYCLES` carries nine values, the roster declares eight;
   `coordination` is the orphan. Any unit planned in that phase is structurally
   unstaffable. (`_ARTIFACTS` has no such gap — enum and roster match exactly.)
2. **`domains` is an unvalidated free identifier.** `_parse_unit` enum-checks
   artifact, lifecycle, authority, mutation and parallelization, but domains go
   through `_items(..., identifiers=True)` with no allowed set. The planner is
   *shown* the roster's 30 domains by `_known_intent_vocabulary` and merely
   asked to use them, so an invented domain parses cleanly and is uncoverable.

Both explain the observed behaviour exactly: deterministic per plan, identical
on retry, and nondeterministic across runs because the planner picks differently
each time. **The retry cannot help, because the repair prompt is addressed to
the recruiter and the plan is what is wrong.** That also explains why the canary
"passed this stage" on one run and failed on the next with no code change.

Three candidate fixes, which differ in what they do to evidence and should not
be chosen casually:

- **Validate domains at plan parse.** An invented domain becomes an invalid
  plan with a planner-targeted repair, instead of surfacing as a recruiter
  failure two stages later. Narrowest, and it puts the error where the fault is.
- **Give uncoverable axes the stack wildcard.** `_coverage` already treats an
  axis no contract declares as neither proven nor disproven for stacks. Applying
  that to domain and lifecycle would absorb both gaps, but it weakens the
  sufficiency proof the verifier exists to make.
- **Route the repair by fault.** Send structural failures back to the planner
  and semantic ones to the recruiter. Most correct, largest change.

Whichever lands, the receipt should also name **which requirement axis was
uncoverable**, not just the unit. The axis names are a closed six-value
vocabulary, so this costs no evidence bounding, and without it every future
occurrence needs the same offline reconstruction this one did.
