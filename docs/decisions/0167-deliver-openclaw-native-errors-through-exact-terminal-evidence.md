---
title: "Deliver OpenClaw native errors through exact terminal evidence"
status: accepted
category: decisions
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, errors, delivery, finalization, security]
related:
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/node_bridge.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
id: ADR-0167
type: decision
deciders: [maintainers]
---

# ADR-0167: Deliver OpenClaw native errors through exact terminal evidence

## Context

OpenClaw 2026.7.1-2 does not call `before_agent_finalize` when its native agent
ends in an error without a visible natural answer. It does emit `agent_end`
with a success bit and later constructs a final reply payload marked
`isError`. Agency's OpenClaw bridge previously routed that payload through the
ordinary authored-answer gate. Because a native error notice has no five-line
Agency header, the Store correctly finalized the turn `response_invalid` and
the outbound gate canceled delivery. Telegram therefore showed silence instead
of the host's error.

A live restart-safety review exposed this boundary after Agency workforce
inference had already succeeded. The native parent accumulated a large
read-only tool context and stopped at OpenClaw's context guard. Suppressing the
error did not protect answer integrity; it hid an already-terminal native
failure from the operator.

## Decision

Treat an OpenClaw-native error notice as a terminal host diagnostic, not an
Agency-authored answer. The generated OpenClaw plugin observes `agent_end` and
may arm one short-lived authorization keyed to the exact native session and
run only when that event reports failure. A later successful event for the same
identity clears the authorization because a failed provider or harness attempt
may precede successful fallback.

The final reply-payload hook may consume that authorization only once and only
when the payload is final, explicitly marked `isError`, and carries the same
session/run identity. Before delivery, a dedicated Agency bridge action must
close the exact correlated active Store turn with terminal failure evidence and
return an authoritative receipt. The plugin then applies the existing outbound
marker and permits the host-owned error payload. Wrong identity, absence,
expiry, replay, non-error payloads, non-authoritative Store results, and bridge
failure remain canceled.

Do not persist or classify raw native error text. The Store receipt records the
terminal category and correlation only. This exception does not make the error
an accepted Agency response, does not satisfy the five-line header contract,
and cannot be used as live activation, staffing, delivery-success, or
actual-model evidence.

Ordinary answers continue through ADR-0049's full-payload finalization and
ADR-0120's exact header contract. Native control acknowledgements retain their
separate exact bounded authorization. Child-delivery gates, OpenClaw source and
configuration, native `task-general`, Agency `task-agency-router`, Hermes, and
all protected harnesses remain unchanged.

## Consequences

- Telegram and other native channels can surface an exact OpenClaw error instead
  of appearing dead while Agency remains fail-closed for ordinary answers.
- Store evidence distinguishes a delivered native failure from an accepted
  Agency response; routing receipts alone still never imply success.
- The authorization map is bounded, expiring, one-use, and content-free. A
  successful fallback cannot inherit an earlier failure authorization.
- Installation support now depends on the audited `agent_end` hook in addition
  to the existing OpenClaw middleware and final-delivery hooks.
- Fresh live proof is still required. Delivering an error does not satisfy the
  substantive OpenClaw acceptance set.

## Alternatives

- Continue suppressing native errors. Rejected because it converts an explicit
  host failure into channel silence and obstructs safe operator recovery.
- Allow every payload with `isError`. Rejected because payload metadata alone
  is not exact turn authority and would bypass Store correlation.
- Add or repair the five-line header on the error. Rejected because that would
  rewrite a failed natural response and could misrepresent failure as Agency
  completion.
- Send an error directly from Agency. Rejected because it bypasses host-owned
  delivery and can duplicate or escape the native outbound boundary.
- Change OpenClaw's model, context limit, source, or host configuration.
  Rejected because the defect is Agency's classification of an existing native
  error surface, not inference routing or host configuration.
