---
title: "Deliver accepted OpenClaw finalizer results instead of silent replies"
status: in_progress
category: roadmap
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, finalization, telegram, delivery, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-277-keep-openclaw-finalization-first-pass.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - agency_runtime/core/installer_payload_openclaw.py
  - tests/test_security_turn_boundaries.py
  - tests/test_adapter_parity.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-278
priority: p0
tracker_url: null
depends_on: [AR-272, AR-277]
blocks: [AR-119, AR-264]
---

# AR-278: Deliver accepted OpenClaw finalizer results instead of silent replies

## Problem

A user-initiated Telegram turn reached OpenClaw and Agency, called
`agency_finalize` successfully, and committed a Store-backed status response.
The native host model then emitted exact `NO_REPLY`. OpenClaw suppresses that
sentinel before `reply_payload_sending` or `message_sending`, so Telegram
queued no response even though Agency's Store terminal record was valid.

This is a post-finalizer host-delivery defect. It is not Telegram ingress,
LiteLLM inference, Agency preflight, or Store finalization success. A Store row
without the host-written response remains insufficient delivery evidence.

## Current state

Opaque native session `6d16c446-4d60-460d-b1ad-d534c72327db` began with exact
user text `agency status`. Trace `9ac12abc-211d-4d4d-9bd1-036b67bda388`, Store
run `669d28d1-8ec1-4a2d-a7fa-4c6e195d1da7`, request binding
`rmb-fef54dccff0a71da62d23ec36ae83a1b`, deterministic routing
`3c9e6fd8-3fce-4d49-92de-d465c30cf238`, and finalization
`63140215-61d6-45ee-9d5a-7f92955569d8` correlate. The finalizer returned the
exact five-line deterministic status header and body; the next assistant event
was `NO_REPLY`. Native transcript SHA-256 is `fd8dc854...`; no channel reply
was queued. No channel/user numeric identifier is retained.

OpenClaw 2026.7.1-2 explicitly skips an exact silent final payload before its
outbound hooks. Its supported `before_agent_finalize` path also bypasses
expected silent replies, and supported post-normalization hooks cannot recover
the payload. Direct channel sending from Agency would bypass or duplicate the
host-owned delivery contract and is rejected.

The focused expected-red exits 223 because the generated finalizer metadata
does not say that it is non-delivering. The minimal candidate replaces
ambiguous “constructs and commits” wording with “validates and returns,” says
the tool result is not delivered, requires the next and final assistant output
to copy the result byte-for-byte, and forbids `NO_REPLY`. Three finalizer tests
and generated-installer parity pass. An ambient-umask parity failure is retained;
the documented private-umask run passes.

## Approach

Change only Agency's generated OpenClaw tool metadata. Do not add a model
revision, rewrite an invalid natural response, send directly from the tool,
alter OpenClaw configuration, or weaken the Store-backed outbound seal. Install
Agency only into a natively stopped OpenClaw gateway from a clean checkpoint,
restart natively, and use a genuinely changed user-initiated Telegram input.

This conforms to ADR-0049 and ADR-0120 and requires no new durable decision.

## Dependencies

- AR-272 provides the Store-backed native finalizer.
- AR-277 makes that finalizer mandatory as the last first-pass tool.
- OpenClaw 2026.7.1-2 supplies the audited prompt-guideline and final-payload
  suppression contracts.

## Acceptance

- [x] Preserve the original Telegram transcript and correlated Store rows.
- [x] Prove exact `NO_REPLY` suppression occurs before Agency outbound hooks.
- [x] Add an expected-red for non-delivery and silent-sentinel guidance.
- [x] Make the smallest generated-prompt correction with no second model pass.
- [x] Keep OpenClaw native routing and all protected-host configuration untouched.
- [ ] Run affected focused tests and local documentation/lint gates.
- [ ] Commit a clean substantive/ledger checkpoint before host mutation.
- [ ] Install Agency only into stopped OpenClaw and restart it natively.
- [ ] Deliver a genuinely changed fresh Telegram response with matching Store evidence.
- [ ] Preserve post-live Store integrity, launcher provenance, and config hashes.
- [ ] Tracker creation remains pending separate authorization.
