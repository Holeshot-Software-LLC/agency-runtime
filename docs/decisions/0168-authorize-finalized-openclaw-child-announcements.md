---
title: "Authorize finalized OpenClaw child announcements"
status: accepted
category: decisions
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, native-child, delivery, finalization, security]
related:
  - docs/roadmap/issue-AR-281-deliver-finalized-openclaw-child-announcements.md
  - docs/roadmap/issue-AR-282-persist-openclaw-child-terminals-after-delivery.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/node_bridge.py
supersedes: []
superseded_by: null
id: ADR-0168
type: decision
deciders: [maintainers]
---

# ADR-0168: Authorize finalized OpenClaw child announcements

## Context

OpenClaw 2026.7.1-2 intentionally returns from `sessions_spawn` before the
child completes. A direct-message completion is then mediated by a requester
agent turn whose host-derived run identity is
`announce:v1:<child-session>:<child-run>`. OpenClaw requires that turn to use
the `message` tool and suppresses automatic source delivery. The tool reaches
`message_sending` without traversing Agency's full reply-payload gate, so the
existing unmarked-message rule correctly cancels it.

Allowing every message-tool call, trusting announcement prose, or waiting for
`subagent_ended` would be unsafe or ineffective. The public provenance-writing
hook has no authoritative run identity, while `subagent_ended` occurs only
after announcement delivery and cleanup.

## Decision

Authorize only the exact completion run deterministically derived from the
host-issued child session and child run retained at an accepted
`sessions_spawn` result. Treat that completion identity only as the authenticated
trigger: the Store must also resolve the same requester to the original parent
session, trace, work unit, worker, launch binding, reciprocal delegation and run
joins, and exactly one ready, active, nonterminal OpenClaw parent with an open
child.

Use the host-owned `announce:v1:` run prefix only to classify an unresolved
completion for denial. Never split its colon-delimited suffix or use the prefix
to recover identities or grant authority. Conflicting nonempty event/context
run identities and process-state loss fail closed before ordinary preflight.

Before ordinary Agency preflight, prepare a dedicated completion context that
instructs the requester agent to emit the exact five-line **parent** header and
body through exactly one `message(action="send", message=<text>)` call. The call
uses the implicit current-source destination and may contain no other tool
fields. This path does not perform workforce inference, record a model receipt,
or create a synthetic `announce:v1:...` Agency run.

Immediately before tool execution, re-resolve the durable completion mapping,
reconstruct and hash-check the prepared context, and pass canonical
`{text: message}` through the original parent's existing outbound gate. Require
an authoritative completed terminal binding, exact canonical payload hash,
exact parent turn, and echoed completion/child identities. A blind or
unavailable-policy allowance is not terminal-bound and cannot authorize this
delivery. Any explicit target, channel, account, thread, reply, media,
presentation, or other delivery surface is rejected.

On acceptance, append the existing random invisible one-use marker to only the
message text and authorize that exact marked value for the completion run. The
terminal `message_sending` hook consumes and strips it. Mutation, replay,
ambiguity, a second send, and uncorrelated message-tool calls remain blocked.
No unmarked-message exception is added.

The child-end callback records the first immutable child outcome but does not
close lifecycle evidence. OpenClaw 2026.7.1-2's `message_sent` hook is the
post-adapter result: only its explicit success may atomically mark the
announcement delivered and close the worker and delegation. Explicit send
failure remains open. Generic child-end handling cannot bypass that delivery
gate.

The audited host exposes no immutable attempt identifier shared by every
`message_sending` and `message_sent` path. Record every allowed textual send in
a bounded attempt ledger and require one unique active match across every
supplied target, channel, account, conversation, session, run, and canonical
content field. Retain active attempts beyond the transport/recovery horizon
and consumed ambiguity tombstones beyond plausible delayed callbacks. Stale,
replayed, delayed, or ordinary-identical receipts cannot prove delivery;
capacity exhaustion fails closed instead of evicting evidence.

If the gateway restarts with a durable child outcome whose delivery is still
`pending` or explicitly `failed`, mark only that receipt-backed lifecycle
`interrupted`, preserve the observed execution outcome separately, and close
the lifecycle as failure atomically. Do not sweep unobserved open workers. A
crash after platform acceptance but before the Store commit is irreducibly
ambiguous and must resolve as `interrupted`, never as delivered. Neither this
operational receipt, the launch binding, nor a terminal child row is a Rule 4
child-card-delivery receipt.

## Consequences

- A finalized OpenClaw child completion can reach Telegram through the host's
  required message-tool-only path without changing OpenClaw or channel config.
- Ordinary message-tool sends remain blocked, and the completion grant cannot
  redirect content to another destination or carry unverified media.
- Completion policy is evaluated and terminally bound on the original parent
  trace before the side effect, preserving first-pass and finalization
  guarantees without inventing an announcement run or receipt.
- Orphan and ambiguous completion runs cannot become ordinary Agency turns or
  create synthetic preflight, inference, model-receipt, or finalization rows.
- A gateway restart reconciles only receipt-backed pending or failed child
  outcomes as interrupted; it never invents delivery or sweeps unobserved work.
- The focused implementation gate passes 294 tests with one existing skip;
  live OpenClaw installation and Telegram delivery evidence remain pending.
- No OpenClaw source/configuration or native model route changed, and the
  decision does not modify Hermes, Codex, Claude, or ZCode.
- Live parent delivery proves operational delegation only. Rule 4 remains
  unproven until ADR-0156's host-artifact requirement is met.

## Alternatives

- Allow all `message` sends after preflight. Rejected because explicit targets
  and non-completion turns would expand the outbound authority boundary.
- Finalize a synthetic announcement trace. Rejected because it would invent an
  Agency run and detach the outbound decision from the parent response whose
  delivery is being completed.
- Parse announcement prompt text or internal provenance. Rejected because the
  supported hooks do not expose an authoritative run-bound provenance field.
- Authorize from `subagent_ended`. Rejected because OpenClaw emits it after the
  completion delivery attempt.
- Send directly from Agency. Rejected because it bypasses host-owned delivery
  and can duplicate a later host announcement.
- Change OpenClaw source, model, or configuration. Rejected because the needed
  correlation and mutation surfaces already exist in the audited plugin API.
