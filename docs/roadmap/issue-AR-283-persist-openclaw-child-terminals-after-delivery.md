---
title: "Persist OpenClaw child terminals after announcement delivery"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, native-child, lifecycle, delivery, cleanup]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0169-authorize-finalized-openclaw-child-announcements.md
  - agency_runtime/core/installer_payload_openclaw.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-283
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-283: Persist OpenClaw child terminals after announcement delivery

## Problem

OpenClaw 2026.7.1-2 completed and delivered a real `sessions_spawn` child result
through Telegram, but Agency left the matching worker and delegation open.
With `cleanup: delete`, OpenClaw removes the child registry entry before its
deferred completion-ended hook can verify that the entry is still current. The
check suppresses the usable `subagent_ended` callback, so Agency never receives
the terminal event it expected.

The child `agent_end` hook precedes announcement transport. Persisting the
worker there is unsafe because Agency's completion resolver requires an open
worker until the finalized announcement is prepared and accepted by the
platform. The completion run's `agent_end.success` is also not a transport
receipt. Only OpenClaw's `message_sent` hook reports the post-adapter delivery
result needed to distinguish an accepted announcement from an explicit send
failure.

## Current state

- The installed `933d9f4a` build's failed live draw is retained. Parent run
  `0191a16c-d5cf-485b-bfa0-70199097ef95`, trace
  `29e96603-cfdc-4ec4-8c86-993b6c9179b7`, native run
  `368bcc67-c1ef-43a7-bf3e-28bd751e8648`, and delegation
  `d6ceb33a-cf76-4c23-aee5-4d221f35255b` correlate one child whose response
  reached Telegram. Agency's worker remained open and the delegation remained
  `delegated` after `cleanup: delete` removed the host registry entry.
- The draw used automatic OpenClaw profile `linux-task-agency-router`, provider
  type `litellm`, and exact requested alias/model-group `task-agency-router`
  with zero cross-provider fallback. OpenClaw's separate native execution
  remained on `task-general`; provider telemetry supplied no actual-model
  receipt.
- The installed Store remains schema 47. The uninstalled candidate advances
  the Store to schema 48 and adds bounded native-terminal observation and
  delivery state to `worker_runs`.
- Child `agent_end` records the first immutable terminal outcome and a
  `pending` delivery state without closing the worker. Conflicting outcomes or
  ambiguous worker correlation fail closed.
- `message_sending` consumes the one-use completion authorization and records
  every allowed textual send in a bounded in-flight attempt ledger. It does not
  claim delivery. Active attempts remain for at least one hour, consumed
  ambiguity tombstones remain for 24 hours, and capacity exhaustion cancels a
  new send instead of evicting correlation evidence.
- OpenClaw's post-transport `message_sent` callback must consume exactly one
  active attempt. It uses requester session, run, and canonical content hash
  when those host fields are present; a shape that omits session or run must
  still have exactly one ledger match. Stale, replayed, ordinary-identical,
  zero-match, and multiple-match callbacks fail closed.
- Only `message_sent(success=true)` changes `pending` to `delivered` and closes
  the worker and delegation atomically. `success=false` changes the state to
  `failed` and deliberately leaves the lifecycle open.
- `gateway_start` reconciles only receipt-backed `pending` or `failed` rows as
  `interrupted`, preserves the immutable observed child outcome in its
  dedicated field, and terminalizes the lifecycle as failure in one atomic
  Store transaction. Unobserved open workers are not swept.
- Generic native-child end handling refuses delivery-gated rows in `pending`
  or `failed`, so a late `subagent_ended` callback cannot bypass the transport
  decision. Exact replays are idempotent; conflicting replays fail closed.
- The schema-48 runtime was integrated with current `origin/main` as
  `5511300e`, ledgered by `7295f289`, installed Agency-only into audited
  OpenClaw 2026.7.1-2, and retained the byte-identical native host config.
- Live parent `c067362a-8bf1-46db-a6d5-85f21a847744`, trace
  `079b9ba8-6dd6-4885-be6e-ad51db7ddc03`, native run
  `dc60b3b9-916e-4d4a-99f7-0e0786d3ebdc`, and delegation
  `0d9f02a8-3610-4367-93b8-90a68fe62835` now pass the post-send gate: outcome
  `ok`, delivery `delivered`, worker ended with exit 0, delegation `completed`,
  parent finalized, and the exact result reached Telegram.
- Parent and child inference receipts stayed on `linux-task-agency-router` /
  `litellm` / exact `task-agency-router`, with no fallback and no supplied
  actual-model telemetry. Operational delivery still is not Rule 4 evidence.

## Approach

1. Persist the first bounded child-terminal observation against the exact
   accepted launch without changing `ended_at`, `exit_code`, or delegation
   state.
2. Retain the exact finalized response hash when `message_sending` consumes the
   one-use authorization, while treating that pre-transport hook as no evidence
   of platform acceptance.
3. On `message_sent`, require the matching finalized parent response and one
   unique active send attempt, using exact session/run/hash fields whenever
   supplied. Retain consumed and delayed ordinary attempts as bounded
   ambiguity evidence. Atomically record `delivered` and terminal lifecycle
   only for explicit success; record `failed` without terminalization for
   explicit failure.
4. On `gateway_start`, atomically mark only durable receipt-backed
   `pending`/`failed` observations `interrupted`, preserve their observed
   execution outcome, and close their lifecycle as failure. Leave unobserved
   open work unchanged.
5. Make first observation and first delivery result immutable, idempotent on
   exact replay, and fail closed on conflicts, ambiguity, malformed identities,
   or attempts to bypass the delivery gate through generic end handling.

## Dependencies

- AR-281's accepted native-child launch and host-profile correlation.
- AR-282's exact one-use finalized child-announcement delivery.
- OpenClaw 2026.7.1-2's audited child, announcement, `message_sending`,
  `message_sent`, and cleanup hook ordering.
- Tracker creation requires separate authorization and remains pending.

## Acceptance

- [x] Expected-red coverage proves child `agent_end` must not terminalize the
      worker before completion preparation.
- [x] Store-focused coverage proves immutable observation, successful atomic
      delivery terminalization, explicit failure remaining open, generic-end
      bypass rejection, idempotent replay, and bounded startup interruption.
- [x] Generated-plugin coverage proves post-send success, explicit failure,
      exact/unique attempt correlation, duplicate-send rejection, stale and
      delayed ordinary-identical ambiguity rejection, and restart
      reconciliation.
- [x] Focused OpenClaw, Store, installer, and dispatch gates pass on the final
      candidate: 294 passed and one unrelated platform skip.
- [x] Independent review has no unresolved Critical, High, or Medium finding.
- [x] Install the clean Agency-only candidate while OpenClaw is natively
      stopped; do not change OpenClaw source or native configuration.
- [x] A fresh changed Telegram draw delivers the child result and closes the
      exact Agency worker and delegation.
- [x] Hermes, Codex OAuth/configuration/canary, Claude, ZCode, native
      `task-general`, and Agency's exact `task-agency-router` route remain
      outside the mutation.
- [x] Operational delivery remains distinct from ADR-0156 Rule 4 proof; no
      matrix cell moves without a host-authored pre-speech artifact receipt.
- [x] A crash after platform acceptance but before the Store commit remains an
      irreducibly ambiguous boundary: startup records `interrupted`, never
      `delivered`, because no durable post-send success receipt exists.
- [ ] Tracker creation remains pending separate authorization.
