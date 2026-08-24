---
title: "Deliver finalized OpenClaw child announcements"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, native-child, telegram, finalization, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-persist-openclaw-child-terminals-after-delivery.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0168-authorize-finalized-openclaw-child-announcements.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/node_bridge.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-281
priority: p0
tracker_url: null
depends_on: [AR-278, AR-280]
blocks: [AR-119]
---

# AR-281: Deliver finalized OpenClaw child announcements

## Problem

OpenClaw 2026.7.1-2 runs `sessions_spawn` asynchronously. For a Telegram
direct-message requester, its authenticated completion turn uses the exact run
identity `announce:v1:<child-session>:<child-run>` and requires the requester
agent to publish through `message(action="send")`. That transport bypasses
`reply_payload_sending`; Agency's terminal `message_sending` hook therefore
cancels the unmarked text before Telegram queues it.

The retained live failure proves the child completed and OpenClaw repeatedly
attempted the completion send, but the Store child lifecycle remained open and
no response reached Telegram. This is an Agency bridge defect, not a LiteLLM,
Telegram-ingress, native-model, or OpenClaw configuration failure.

## Current state

- The first live native-child staffing attempt also exposed a separate
  15-second inherited judge deadline and a process-local end-callback
  dependency; both are within AR-280's host-profile and lifecycle scope.
- OpenClaw's completion-run identity is derived from host-issued child session
  and run values already captured by Agency at the accepted spawn result.
- `subagent_ended` fires after completion delivery and cleanup, so it cannot
  authorize the current announcement.
- Ordinary direct message-tool sends remain untrusted and must stay blocked.
- The implemented bridge now recognizes only the exact retained completion
  identity, prepares a dedicated message-tool-only completion context, and
  finalizes the candidate against the original parent trace. It does not create
  a synthetic announcement run, repeat workforce inference, or attach a model
  receipt to the completion turn.
- A host-authenticated `announce:v1:` run that is orphaned, ambiguous, or has
  conflicting hook identities is classified only for denial and cannot fall
  through to ordinary preflight. The prefix is never split into identities or
  used to grant completion authority.
- The Store resolver requires the exact requester, parent trace and work unit,
  child session and run, accepted launch binding, reciprocal delegation/run
  joins, and one unique ready nonterminal OpenClaw parent with an open child.
- The consolidated focused gate passes 299 tests with one existing skip. The
  clean implementation/ledger checkout `27e9ec62` is now installed through
  Agency's installer only while OpenClaw was natively stopped. The gateway was
  restarted natively; RPC is healthy and the Agency plugin is loaded, enabled,
  and activated with all 12 hooks.
- The installed bundle/runtime digest is `0c2bb3fc...` and the launcher SHA-256
  is `e9169d04...`. Native `litellm/task-general` plus all six fallbacks remain
  exact, and the semantic config diff excluding its native timestamp is empty.
  The live service has `LITELLM_API_KEY` populated; its value was not read.
- Hermes remained active and its config, environment, and launcher hashes are
  unchanged.
- The fresh Telegram `/new` was acknowledged. Parent run
  `a0f349c8-712d-4702-bc14-ac2e8e0e4ee1`, trace
  `856341f9-40f0-49f7-99fd-ba39a4a4a6c8`, and transcript
  `4ad38fad-d167-4310-a4e7-2a0c8f189646` launched one native worker. Worker
  `agent:nexus:subagent:e0ee5df5-a66e-4085-b7e1-19bb41dbfed5`, native run
  `b182db5c-1764-4d83-a0be-c5a0575ac828`, and child transcript
  `bf9127d3-6436-49a6-bf28-9af373ab371e` prove execution and successful
  completion of the read-only child task. Agency then blocked completion as
  uncorrelated before Telegram queueing; no completion reached the operator.
- Canonical route `ba9e00d0-b2ac-4ffb-a1ce-7b2c27a53d4c` and native-child
  route `native-child-eaa40e37d3a5dad02a475e9a38fca63d` are both valid. The
  child route contains one applied `litellm` attempt on profile
  `linux-task-agency-router` for exact alias/model-group `task-agency-router`,
  zero fallback, and no provider-supplied actual-model receipt.
- Ready-receipt integrity incorrectly required one total routing row. The valid
  `native_child_inference` row appended after canonical preflight therefore
  made completion preparation return empty. Every durable identity predicate
  passed; cleanup occurred after denial, and restart/reload, timeout, TTL, and
  identity mismatch are ruled out.
- The locally green Agency-only candidate accepts exactly one canonical route
  plus only unique auxiliary rows that strictly re-project as complete
  native-child success routes. It validates exact route IDs, canonical Store
  timestamps and context digests, exact numeric types, canonical JSON fields,
  and unique host/launch identities. Duplicate, unrecognized, malformed, or
  type-shifted evidence fails closed.
- Independent Critical/High review is green after the duplicate, timestamp,
  numeric, JSON, context-digest, and route-ID gaps were closed. Focused tests
  pass 113 with 1 skip; the named fast spine passes 848 with 3 skips. Docs
  metadata/policy/worklog/verification pass for 780 files and 1,155 commits;
  full Ruff check/format pass 682 files; dashboard UI passes 134; routing eval
  passes; full decision conformance passes baseline and kills 160/160 with zero
  survived/invalid and source unchanged; diff check passes.
- The default private-HOME full eval lacked `pytest`; the changed `.venv` retry
  failed the trusted persistent-interpreter boundary; the owner-private eval
  venv based on `/usr/bin/python3` passed. No exhaustive workflow corpus ran.
- Clean correction/ledger `c7520586` / `2bf42059` is installed from the exact
  checkout; evidence root is
  `/home/holeshot/.agency-runtime/evidence/ar281-openclaw-c7520586-4ceF3vbq`.
  Pre-install online Store backup `736434a7...`, source, and backup are `ok` at
  schema 47. OpenClaw 2026.7.1-2 was stopped natively while Hermes stayed active.
- Agency-only/no-dashboard install completed without restarting the gateway;
  backup path is `~/.agency-runtime/backups/openclaw/20260824T195320.228690Z`.
  Bundle `ae5b0a3e...`, runtime `46ed926c...`, install `ed2572b6...`, and
  launcher `46c4fd6e...` bind to the correction checkout. Native restart restored
  service/RPC and 12 loaded/enabled/activated hooks.
- Agency config `43367ec9...` retains only `api_key_env`; credential presence is
  true without value access. OpenClaw semantic config `5f806455...`, native
  `task-general`, and six fallbacks are unchanged; contractors are 15/15 and
  post-install Store is `ok`/47. Hermes config/env/launcher remain unchanged and
  no Hermes install occurred. Expected config-validation degradation is from
  cold inventory, protected hosts, and the legacy-provider warning.
- The changed second draw is now retained. Parent `db9fb4f4...` / trace
  `1dc07325...` / transcript `ba29f451...` spawned exactly one child session
  `82abcc6d...`, native run `cf704bcb...`, delegation `0f2ea05c...`, worker row
  `native-child:0b0cf133...`, and route `native-child-c8e004f5...`. The child
  completed at `20:18:26Z`, but its first completion failed
  `FINALIZATION_UNAVAILABLE`; 12 further attempts were uncorrelated. No
  Telegram send or finalization/delivery row exists, and Store lifecycle stays
  active/delegated/open.
- The child route again used `linux-task-agency-router` / `litellm` / exact
  `task-agency-router` with zero cross-provider fallback and no actual-model
  telemetry; native OpenClaw stayed on `task-general`.
- Authorization supplied `headerContextHash`, but `serializeBridgePayload`
  omitted it before Python finalization. The expected-red preceded the
  one-line bounded-field forwarding fix. The four-file suite passes 145/1
  under `umask 077`; targeted Ruff/format/diff pass and independent review is
  GREEN. Candidate is not installed; OpenClaw stopped cleanly, Hermes remained
  active/untouched, and there is no live-fix claim.
- Strict Rule 4 remains unproven because a delivered announcement is not a
  host-authored pre-speech child-artifact receipt.

## Approach

1. Match only the exact host-derived completion run against one started,
   pending native-child state, its exact requester session, and the durable
   parent/child/launch/delegation joins in the Store. Deny any unmatched or
   conflicting host completion run before ordinary preflight.
2. Before ordinary Agency preflight, prepare a dedicated completion context
   that requires the exact five-line parent header and exactly one
   `message(action="send", message=<text>)` call to the implicit current
   destination. Do not run ordinary workforce inference or create an
   announcement Store run.
3. Immediately before that tool side effect, re-resolve the durable mapping,
   reconstruct and hash-check the prepared context, and pass canonical
   `{text: ...}` through the original parent's outbound gate. Require an
   authoritative completed terminal binding, exact payload hash, parent turn,
   and echoed child identities.
4. Reuse the existing random one-use invisible dispatch marker so
   `message_sending` strips and consumes the exact grant. Reject ambiguity,
   mutation, replay, a second send, and any uncorrelated run.
5. Let the later `subagent_ended` callback close the still-open child lifecycle
   idempotently without replacing the already committed parent terminal
   response. Preserve host transcript and Store evidence separately; do not
   promote this transport receipt into Rule 4 proof.

## Dependencies

- OpenClaw 2026.7.1-2's audited `sessions_spawn`, `before_tool_call`, and
  `message_sending` contracts.
- AR-278's exact finalization and terminal message seal.
- AR-280's host-scoped child staffing and durable lifecycle correlation.
- Tracker creation requires separate authorization and remains pending.

## Acceptance

- [x] Expected-red coverage reproduces the exact authenticated completion run
      being suppressed before delivery.
- [x] Generated-hook coverage proves one exact finalized, text-only,
      implicit-destination completion send is marked and consumed once.
- [x] Wrong requester, child, run, target, envelope, hash, terminal decision,
      ambiguity, mutation, replay, and second-send cases fail closed.
- [x] Completion preparation/finalization reuses the original parent trace,
      creates no synthetic announcement run or inference receipt, and remains
      stable when the later child-end receipt closes lifecycle evidence.
- [x] The focused implementation gate passes 299 tests with one existing skip.
- [x] Install the clean `27e9ec62` Agency-only candidate while OpenClaw is
      natively stopped, then restart it natively with RPC and all 12 Agency
      hooks healthy and no semantic native-config drift.
- [x] Preserve the changed live draw in which one child executed and completed,
      but ready-routing receipt integrity blocked completion before Telegram.
- [x] Independent Critical/High review and the focused, fast-spine, docs, Ruff,
      dashboard, routing-eval, and 160-mutation conformance gates pass.
- [x] Checkpoint the locally green correction as `c7520586` / `2bf42059` and
      install it through Agency only while OpenClaw is natively stopped.
- [x] Preserve the second changed draw's exact `headerContextHash`
      serialization failure, add an expected-red first, and pass the focused
      four-file and targeted static gates with independent review GREEN.
- [ ] A fresh OpenClaw native child returns one finalized Telegram response with
      correlated Store lifecycle evidence.
- [x] No OpenClaw source/configuration, native model routing, Agency inference
      alias, Hermes, Codex OAuth/configuration/canary, Claude, or ZCode changes
      are authorized by this issue.
- [x] Rule 4 remains unproven without an ADR-0156 host artifact receipt.
- [ ] Tracker creation remains pending separate authorization.

## 2026-08-24 operational delivery passed; Agency terminal receipt missed

Installed `10ba4c84` / `8a2bf9b7` produced the first fresh changed draw in this
package whose exact inference header and child result reached Telegram. Parent
run `5529c6cf...` / trace `a5f6f53b...` spawned one child, and OpenClaw's task
ledger records `succeeded` / `delivered`. Canonical route `99f1388a...` and
child route `native-child-4ef0e65f...` used
`linux-task-agency-router` / `litellm` / exact `task-agency-router` with zero
cross-provider fallback. Native OpenClaw execution stayed separately on
`task-general`; actual answering model remains unavailable.

The Store parent completed, but delegation `79049f17...` and worker
`native-child:9ea15e2f...` stayed nonterminal. Exact isolated replay closes both,
so the defect is the generated plugin's one-shot callback handling, not Store
identity or LiteLLM routing. Observation-only end state was swallowed, while a
failed trace-bound terminal receipt depended on a duplicate end hook. A first
partial repair was kept out after review found unhandled early-end and sparse
reset/delete forms. The final exact-state durable fallback was preceded by
expected-red coverage, passes focused 146/1, fast spine 849/3, all local gates,
and 160/160 conformance mutations, with no Critical/High/Medium re-review finding.

The candidate is not installed. Operational transport succeeded once, but the
acceptance item remains unchecked until a changed installed draw also closes
the delegation and worker. No `native_child_delivery_verifications` row was
fabricated; ADR-0156 Rule 4 and the AR-119 matrix remain unchanged.

## AR-282 post-transport lifecycle correction

The subsequently installed `933d9f4a` one-shot terminal-reconciliation build
preserved another operational delivery but did not close Agency lifecycle.
Parent run `0191a16c-d5cf-485b-bfa0-70199097ef95`, trace
`29e96603-cfdc-4ec4-8c86-993b6c9179b7`, native run
`368bcc67-c1ef-43a7-bf3e-28bd751e8648`, and delegation
`d6ceb33a-cf76-4c23-aee5-4d221f35255b` correlate the retained failure.
OpenClaw delivered the child response, then `cleanup: delete` removed the host
registry entry before the expected `subagent_ended` receipt could close the
worker and delegation.

AR-282 owns the replacement. Its uninstalled schema-48 candidate separates an
immutable child-terminal observation from delivery status. `message_sending`
records all allowed text sends in a bounded attempt ledger but does not prove
transport. Only OpenClaw's post-adapter `message_sent(success=true)` with one
unique active attempt may atomically mark the response delivered and close
lifecycle. Explicit send failure remains open; startup reconciles only
receipt-backed pending or failed rows as interrupted lifecycle failures while
preserving observed execution outcome; and generic end/stop handling cannot
bypass the delivery gate. Every supplied target/channel/account/conversation/
session/run field and exact response hash must match. Stale, delayed,
ordinary-identical, replayed, and ambiguous callbacks fail closed.

The candidate passes 294 focused tests with one unrelated skip and independent
review is GO, but it has not been installed.
The retained draw proves operational transport, not correlated Agency
terminalization or ADR-0156 Rule 4.
