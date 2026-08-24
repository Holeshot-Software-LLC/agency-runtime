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
- The consolidated focused gate passes 299 tests with one existing skip. Live
  Agency installation and a genuinely fresh Telegram child response remain
  pending; no host source, configuration, or native model route was changed.
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
- [ ] A fresh OpenClaw native child returns one finalized Telegram response with
      correlated Store lifecycle evidence.
- [x] No OpenClaw source/configuration, native model routing, Agency inference
      alias, Hermes, Codex OAuth/configuration/canary, Claude, or ZCode changes
      are authorized by this issue.
- [x] Rule 4 remains unproven without an ADR-0156 host artifact receipt.
- [ ] Tracker creation remains pending separate authorization.
