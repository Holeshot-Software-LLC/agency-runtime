---
title: "AR-362: Add an agent-chaos harness with explicit failure oracles"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [chaos, testing, battery, reproducibility]
related:
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-352-scope-battery-deltas-by-session.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-362
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/435
depends_on: []
blocks: []
---

# AR-362: Add an agent-chaos harness with explicit failure oracles

## Problem

Our reliability evidence is observational: batteries watch turns and
wait for failures to occur naturally. Intermittent defects therefore
have no repro — the AR-353 staffing window can only be measured by
waiting for it to flap, and the AR-297 review's runner hard-kill
recovery gap has never been exercised deliberately. A defect we cannot
inject is a defect we cannot regression-test.

## Current state

No injection machinery exists. Provider outages, hard kills, and
timing windows are reproduced by luck or not at all.

## Approach

Build a small chaos layer (concept lifted from LobeHub's achaos
packages, owner-approved 2026-09-01) with portable contracts:

- **Experiment**: a named scenario (provider timeout during staffing,
  runner hard-kill mid-run, gateway restart mid-turn).
- **Effect**: the injected fault, applied through owned adapters only
  (hook delivery, provider client, process ownership-checked kills).
- **Safety**: bounds that keep experiments off live user turns —
  dedicated sessions, rollback on exit.
- **Oracle**: the explicit pass/fail judgment (e.g. "run closes
  preflight_failed with a receipt and the next turn fails open with
  Rule-8 pass-through").
- **Receipt**: a stored result row so chaos runs are evidence.

Start with the two named scenarios above; wire results into the
battery report.

## Implementation (2026-09-02)

`agency_runtime/core/chaos/` ships the five portable contracts as frozen
records (`contracts.py`: `Experiment`, `Effect`, `Safety`, `Oracle`,
`Receipt`, each bounded and content-free — reason codes and names are
allowlisted tokens, observations are depth/size-bounded projections) and
two experiments (`experiments.py`):

- `staffing_window` — three cases inject the AR-353 window's shapes through
  the workforce inference invoker seam only: a provider timeout
  (`workforce_provider_unavailable`), an invalid completion
  (`inference_invalid`), and a strict-critic rejection
  (`staffing_critic_rejected`). The oracle requires the run to close
  `preflight_failed` with a persisted receipt carrying the expected stage,
  attempt statuses and staffing codes, the fail-open result to bind the
  steward kernel with status `no_specialist_fail_open`, and
  `turn_closed_without_bound_response` to be true so the Rule-8
  pass-through would publish the next reply.
- `runner_hard_kill` — an owned child process begins a preflight attempt in
  the dedicated store and is SIGKILLed mid-attempt. The recovery oracle
  records current behaviour, gap and all: the run stays `active` /
  `in_progress` under the dead attempt token until its lease lapses, a
  same-trace retry inside the lease sees `reused_in_progress`, the orphan
  is not a `FAIL_OPEN_RUN_STATUSES` member (only the AR-366 in-progress
  gate passes a same-trace draft through), and it closes only through a
  post-lease same-trace retry (`recovered_started`) or the session's next
  turn (`abandoned`). Each of those statements is asserted, then written
  to the receipt's `gap_notes`.

Safety is enforced in code (`safety.py`): every run arms an envelope with a
fresh owner-private runtime home, a dedicated Store under it, synthetic
`chaos-` session ids (`require_session` refuses any other), a process-wide
`AGENCY_CHAOS_MODE` gate effects check before injecting, canonical-path
refusal of the live configured database (default path, `AGENCY_DB_PATH`, and
the loaded config's store), and rollback that removes the home on exit even
when the experiment raises. A raising effect or oracle is a failed receipt
with an exception category, never a crashed harness.

Every run seals `~/.agency-runtime/evidence/chaos/<stamp>-<experiment>/receipt.json`
(0600, schema `agency.chaos-receipt.v1`); `agency chaos run
[--experiment NAME] [--json]` exits 1 on any failed verdict;
`chaos_report_summary` is the bounded projection the battery report can
embed (the battery is not modified here — AR-360's grading loop landed in
parallel and the summary is wired in a follow-up).

Live run on this box (2026-09-02 04:52Z, both experiments pass, receipts
`20260902T045234355398Z-staffing_window` and
`20260902T045240653999Z-runner_hard_kill`).

Tests: `tests/test_chaos_harness.py` — the shipped experiments pass against
shipped behaviour with sealed receipts, the three staffing shapes, safety
refusals (live database, foreign session, unarmed effect), rollback on a
raising effect, a raising oracle as a failed receipt, action scope,
receipt sealing and projection, experiment resolution and summary, CLI.

## Dependencies

- Pairs with AR-360 (trial semantics) for grading repeated experiments.

## Acceptance

- [x] The AR-353 staffing-window shape is injectable on demand and its
      oracle passes against the shipped fail-open behavior —
      `staffing_window` (three shapes), passing live on this box and in
      `test_the_shipped_experiments_pass_against_shipped_behaviour`.
- [x] A runner hard-kill experiment exists and its recovery oracle
      records the current behavior (pass or documented gap) —
      `runner_hard_kill` passes with four recorded gap notes (the orphan
      stays `active`/`in_progress` until its lease lapses).
- [x] Experiments run only in dedicated sessions with rollback, never
      against live user turns, enforced in code —
      `test_safety_refuses_the_live_database_and_foreign_sessions`,
      `test_effects_apply_only_inside_an_armed_envelope`,
      `test_a_raising_effect_is_a_failed_receipt_and_still_rolls_back`.
