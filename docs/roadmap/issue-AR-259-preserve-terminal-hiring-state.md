---
title: "AR-259: Preserve terminal hiring state after atomic preflight failure"
status: in_progress
category: roadmap
created: 2026-08-20
updated: 2026-08-20
tags: [observability, hiring, preflight, evidence, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - agency_runtime/core/preflight_failure.py
  - tests/test_preflight_failure_diagnosis.py
  - tests/test_preflight_bounds.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-259
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/305
depends_on: []
blocks: [AR-119, AR-261]
---

# AR-259: Preserve terminal hiring state after atomic preflight failure

## Problem

The exact-main Claude accepted-outcome draw for pair `fcffd96c...` reached an
applied planner and applied recruiter, then failed with an inference-declared
gap. Its immutable failure receipt retained no hiring reason codes. That does
not prove hiring was skipped: a successful deferred hire intentionally has an
empty reason list, and atomic preflight rolls its pending case back if later
restaffing still fails. The same on-disk receipt can therefore describe either
"no hiring event" or "hiring consumed inference and reached a terminal status."

That ambiguity makes the next live draw non-diagnostic and risks spending more
provider calls to rediscover a state the runtime already computed.

## Current state

- The draw, its provider identities, Store rows, prompt reconstruction, and
  evidence limits are recorded in
  `AR-119-fcffd96c-hiring-diagnostic-evidence.md`.
- `preflight_hiring_reason_codes` currently copies only event
  `reason_codes`. It discards the closed `status` and bounded `calls_used`
  fields from the same event.
- Worker identity, notification text, prompts, response bodies, and pending
  contract content must remain outside the terminal failure receipt.
- Tracker [#305](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/305)
  is open with the required `epic:observability` label.
- Repository-wide `--require-tracker` and tracker-parity audits remain red on
  the pre-existing unauthorized tracker backlog and historical state/label
  mismatches. Neither audit reports an AR-259 mismatch.

## Approach

Project only two additional code classes through the existing bounded
`hiring_reason_codes` array:

1. `hiring_status_<status>` for the closed runtime vocabulary (`abstained`,
   `amended`, `hired`, `not_attempted`, `pending_approval`, `rejected`).
2. `hiring_inference_attempted` when `calls_used` is a positive integer.

Unknown statuses, stringified counts, booleans, identities, notifications, and
model content remain rejected or ignored. The existing receipt schema and
Store migration do not change; old receipts continue to decode exactly as
written.

## Dependencies

- AR-207 owns the existing bounded preflight-failure receipt.
- ADR-0027 requires externally visible claims to derive from authoritative,
  correlated evidence.
- ADR-0112 requires pending hiring mutations to commit only with ready
  preflight evidence.

## Acceptance

- [x] A deferred successful hiring event with empty reasons retains its closed
      status and the fact that inference ran.
- [x] Pending approval and not-attempted outcomes remain distinguishable.
- [x] Untrusted status values and non-integer call counts do not cross the
      evidence boundary.
- [x] A Store-backed terminal preflight test proves the projected codes persist
      and no prompt, response, notification, path, credential, or worker
      identity survives.
- [x] Focused preflight and dynamic-hiring tests pass warning-strict.
- [x] Required tracker issue #305 is created after explicit owner authorization.
- [x] The exact local candidate passes all 12 proportional gates in 1.3 minutes
      at recovery pair `de9ef543` / `13413c53`.
- [x] The candidate is published through reviewed PR #306 as exact main
      `06f10171` with `[skip ci]` and no hosted workflow run.
- [x] A later authorized exact-main draw is decisive at the hiring boundary;
      this issue itself moves no AR-119 matrix cell.
- [ ] Tracker issue #305 is closed after explicit outward-write authorization.
