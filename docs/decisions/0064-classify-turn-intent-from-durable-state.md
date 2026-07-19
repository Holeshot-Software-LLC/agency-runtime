---
title: "Classify turn intent from durable state before selecting expertise"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [routing, lifecycle, correlation, inference]
related:
  - docs/roadmap/issue-AR-85-state-aware-turn-classification.md
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0064
type: decision
deciders: []
---

# ADR-0064: Classify turn intent from durable state before selecting expertise

## Context

Agency previously used a `trivial` or `nontrivial` projection to decide whether
specialist routing and completion enforcement applied. Prompt length and exact
phrase heuristics cannot distinguish a harmless acknowledgement from a short
authorization, continuation, revision, or real request. The same bit also
blurred three independent decisions: what the turn means, what expertise would
help, and whether that expertise belongs in the parent or a native child.

## Decision

Classify each external user turn as exactly one of `acknowledgement`,
`conversation`, `control`, `continuation`, `new_intent`, or `revision` before
specialist selection. Emit independent booleans for selection, rerouting, and
execution-decision requirements.

Use durable current state when interpreting contextual replies: prior trace and
terminal status, open plans, unfinished work, pending questions or
authorizations, retry state, configuration and roster revisions, selected
specialist versions, and delegation state. Missing, stale, ambiguous, or
corrupt state cannot authorize a bypass.

Only a proven pure acknowledgement with current state and no unfinished or
pending work bypasses specialist selection. Exact Agency runtime controls use a
separate deterministic control path. Social conversation remains a distinct
turn kind but still performs roster consideration and may explicitly abstain.

Retain `trivial`, `nontrivial`, and `trivial_msg_threshold` only as bounded
compatibility surfaces. The threshold defaults to zero everywhere and has no
authority in the classifier. A prior plan may be reused only while its
correlation, configuration, roster, specialist, and delegation guards remain
valid; otherwise the affected work reroutes.

Use one canonical exact runtime-control parser in classification, CLI
registration, host control execution, and generated host guidance. Only the
complete `agency [runtime] status|on|off` and `/agency [runtime]
status|on|off` forms are controls. Punctuation, extra text, and broad words do
not gain control authority.

Treat the classifier value object as an authority boundary. Its semantic
boolean matrix, correlation requirements, classifier version, state digest,
and exact raw-message digest are validated at construction. Current decisions
are process-sealed; public routing rejects a structurally valid but unsealed,
cross-message, or older-version object. Legacy persisted projections remain
replayable data but cannot be supplied as current routing authority.

Replies to a pending question or authorization always reroute the affected
work before any contextual-token reuse. A reusable continuation is accepted
only after the durable source recipe and every guard validate. A missing,
stale, or changed correlation, configuration, roster, specialist, delegation,
or work-unit guard causes one bounded fresh route. The ready transaction checks
the source guard again; a commit-time race discards the reuse and reroutes once
rather than publishing manager-only abstention evidence.

Owned adapter boundaries process-seal one exact origin value:
`external_user`, `internal_retry`, `stop_revalidation`,
`automatic_continuation`, or `native_child`. The seal binds the adapter
surface, allowlisted lifecycle event, session, turn, and a short lifetime.
Only `external_user` may begin classification. Internal retries are resolved
from exact durable lifecycle state, never from prompt text or a serialized
marker, and internal origins must reuse or revalidate their existing turn
without starting preflight.

## Consequences

- Short requests and contextual approvals cannot silently bypass Agency.
- Classification receipts explain the matched state and signal codes instead of
  relying on an unexplained generic label.
- Inference and specialist selection can be required without requiring native
  delegation, and delegation can be evaluated independently.
- Legacy stores and integrations remain readable while new surfaces use the
  authoritative typed projection.
- Greetings incur a bounded roster decision rather than an unrecorded bypass;
  calibrated abstention remains valid.
- Host adapters must preserve the typed receipt and cannot treat Stop feedback
  or a retry as a new external turn.
- Direct low-level `run_preflight` callers that omit a valid origin receipt are
  intentionally treated as untrusted and forced through fresh selection; they
  cannot obtain acknowledgement, control, or continuation reuse bypasses.
- Native host APIs do not all expose every lifecycle event. Where a host cannot
  prove an automatic continuation or child lifecycle, Agency records no such
  origin and relies on the host's existing execution lifecycle instead of
  inferring one from message content.

## Alternatives

- Keep a tunable character threshold. Rejected because length does not encode
  intent, risk, authorization, or pending state.
- Expand the acknowledgement keyword list. Rejected because a larger generic
  regex still cannot resolve contextual meaning safely.
- Treat every message as a fresh unrelated task. Rejected because it discards
  valid continuation correlation and needlessly repeats selection and planning.
- Reuse the last selection for every short reply. Rejected because configuration,
  roster, specialist versions, or work-unit state may have changed.
