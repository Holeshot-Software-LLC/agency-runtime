---
title: "Deliver accepted OpenClaw finalizer results instead of silent replies"
status: in_progress
category: roadmap
created: 2026-08-22
updated: 2026-08-23
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
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
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

The first prompt correction exposed a second independent delivery defect. The
model copied the finalizer result exactly, but the finalizer had already
committed a terminal hash of the policy text. OpenClaw's last reply-payload
hook correctly canonicalized the richer outbound envelope and required its
different full-payload hash. The conflicting prior terminal caused the
fail-closed gate to cancel the otherwise valid reply before Telegram queueing.

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

That prompt candidate was checkpointed as `1ca46cc9` / `320dc7cf` and
installed into natively stopped OpenClaw as Agency-only install
`74b4c0bc-8da5-4bfb-ac91-08c6e770c7ea`. OpenClaw stayed 2026.7.1-2 on
`litellm/task-general`; its primary, six fallbacks, and Agency configuration
were unchanged. Opaque fresh session
`80c9c847-ff6d-4d16-b913-50e96b981a42` then produced exact finalizer text,
not `NO_REPLY`. Trace `2eaaf8e9-07f0-475c-89dc-f811553339ed`, run
`27faf92b-4c60-430d-8401-358831c60f29`, routing
`9528aa21-6cce-4a2c-87d8-1e4ba7722b00`, skill row
`0f548ebf-c080-4733-b981-5b21481fd7eb`, and terminal
`9b2d4c3a-121e-4043-8c72-640ebde48e74` correlate. The final text and tool
result match at SHA-256 `202f0d58...`; no Telegram outbound timestamp or
queued response exists.

The retained full-payload expected-red proves the terminal existed immediately
after the tool call with the text hash. The repair leaves OpenClaw finalizer
text pending, lets `before_agent_finalize` validate that exact text, and
atomically commits the canonical outbound-payload hash plus the separate policy
text hash only in the last reply-payload gate. A second expected-red captures
the blocked native `/new` acknowledgement. The narrow repair authorizes one
exact static acknowledgement for exact `/new` or `/reset`, bound to the
session and a ten-second lifetime; replay, tailed commands, and arbitrary
unmarked messages remain blocked.

Agency-only install `87b518e8-dfee-4759-af7d-565705d09afa` then produced a
third retained Telegram failure in fresh session
`ac750af6-7adf-41b9-ba8a-9feee76539e4`. Trace
`4552b87d-5ee3-45a3-ba61-6629bbb20e99`, run
`86d3c0a2-79f0-4ea6-aa0a-adcb4056d25b`, routing
`bbf1d404-bb7b-4eb6-be3d-3b27aaf00786`, and specialist row
`37ad1cc1-72c3-4d9d-b824-0b6eecd482ca` correlate. Three provider-stage
receipts selected the OpenClaw harness, profile `linux-task-agency-router`,
LiteLLM, and exact alias/model-group `task-agency-router` with no protected-host
fallback. The pending finalizer was accepted, but the native terminal was exact
`NO_REPLY` (SHA-256 `b07800ad...`), producing terminal
`9599d181-a104-42a1-b166-8412add9c1d0` with `response_invalid`; Telegram
queued nothing. This proves Agency routing and the alias are healthy and places
the remaining failure after model inference.

The same session exposed a reset race: native reset commands bypass
`message_received`, and OpenClaw starts `before_reset` asynchronously while its
acknowledgement can reach `message_sending` first. The focused regression first
failed, then passed after the generated bridge moved correlation to
`before_reset` and waits up to one second only for either exact native
acknowledgement. Replay, unknown reasons, other text, and cross-session use
remain blocked; the affected security, adapter-parity, and installer suites are
218 passed. This candidate is not installed.

The former return-direct prerequisite is disproven. OpenClaw's terminal
classifier marks a final assistant event ending in tool use as
`non_deliverable_terminal_turn` unless the host records explicit terminal
delivery, so marking `agency_finalize` terminal cannot solve the defect.
However, the supported plugin SDK exposes an awaited
`registerAgentToolResultMiddleware` surface before the model continues. That
is sufficient to persist a native tool observation and refresh exact Store
evidence without changing OpenClaw source, configuration, or model routing.

Lucas selected temporary recovery instead. The ownership-bound Agency uninstall
dry-run failed before mutation because OpenClaw reports its native installed
copy at top level and the managed source only in nested install provenance; this
is retained under AR-269. With the gateway stopped, OpenClaw's native plugin
command disabled only `agency-preflight`, then the native service restarted.
Agency is registered/staged but inactive, RPC and both channel probes are green,
native `litellm/task-general` plus all six fallbacks are unchanged, and Hermes
and protected hosts remain untouched. The operator sent exact `reply with pong`
and received exact `pong`; redacted native channel state records inbound and
outbound activity, and role-aware transcript verification passes at SHA-256
`0420d72c...`. This proves ordinary OpenClaw recovery, not Agency acceptance.

The OpenClaw-only candidate now removes the exposed finalizer tool, supplies an
initial exact five-line Store snapshot at preflight, and registers one awaited
tool-result middleware scoped to runtime `openclaw`. The middleware records the
tool result before appending an updated exact snapshot while preserving the
native result. Missing or disabled refresh returns the host result unchanged.
`before_agent_finalize` still validates the first natural response and the
existing full-payload gate remains authoritative. Expected-red exit 232 is
retained. The affected security, adapter, and installer slice passes 72 tests,
including installer refusal when the middleware contract is absent. ADR-0166
records the host-specific decision. The candidate is not installed; Agency
remains natively disabled and ordinary OpenClaw remains available.

### Fourth Telegram failure: alias-only evidence arrives after authorship

Clean pair `da184b4f` / `773d9080` was installed as Agency-only operation
`514528d9-e373-4f87-b1c0-9d53edb9401b` while OpenClaw was natively stopped.
The installer did not restart it. Native restart loaded ten required hooks, the
awaited middleware scoped to OpenClaw, no exposed tool, and zero diagnostics.
Gateway RPC and Telegram/Slack probes were green. The native config differed
from its exact pre-install backup only at `meta.lastTouchedAt` and
`plugins.entries.agency-preflight.enabled`; primary
`litellm/task-general`, six fallbacks, channels, providers, and credential
indirection remained unchanged.

A fresh reset acknowledgement was absent, but exact `agency status` reached a
new native session. OpenClaw completed three `task-general` requests with HTTP
200, ran native tools, and authored one natural 665-character response beginning
with the exact Store-backed five-line header. The turn kernel nevertheless
reported `no queued reply payloads`. Transcript SHA-256 is `13300aefd4...`.

Agency trace `a9afc0e8-c998-4bff-9c9e-6dce27628bb2`, run
`24104a10-ad68-43a3-9a79-92603687cd1b`, routing
`30f6b37b-610e-4f4c-8fce-593fe4cd6d8f`, and terminal
`625e3e8c-e82c-4918-a23e-5c180760676b` correlate. Control routing correctly
abstained through the deterministic path; no specialist, skill, resident
binding, or Agency workforce inference was expected. Finalization failed closed
with only `actual_model_selected` missing.

The installed OpenClaw hook contract explains the mismatch. Its sanitized
`model_call_ended` event supplies provider `litellm` and requested alias
`task-general`, not LiteLLM's answering model. Agency correctly refuses to
promote that alias into actual-model evidence, but each alias-only completion
had still created an unavailable receipt. The final receipt arrived after the
model authored its requested-alias header, changed the evidence revision, and
made the exact response stale before final validation.

A focused regression first failed by showing that header mutation. The minimal
OpenClaw bridge fix does not persist a LiteLLM hook event when both resolved
provider and resolved model are absent; genuine resolved-model receipts remain
unchanged. The focused OpenClaw adapter, middleware, and finalization slice is
31 passed and 1 skipped. Shared header policy, OpenClaw source/configuration,
native and Agency model routing, outbound gates, and every other harness remain
unchanged.

## Approach

Change only Agency's OpenClaw adapter as specified by ADR-0166. Do not expose
the finalizer tool. Supply the initial exact Store-backed header at preflight,
record native tool evidence through OpenClaw's awaited tool-result middleware,
and append the updated exact snapshot before the model continues. Keep
`before_agent_finalize` as the first-pass validator and the last reply-payload
gate as the complete-envelope commit and authorization boundary.

Retain the exact reset acknowledgement correlation. Do not add a model revision,
rewrite an invalid natural response, send directly, alter OpenClaw source or
configuration, change native or Agency inference routing, or weaken the
Store-backed outbound seal. From a clean checkpoint, install Agency Runtime only
into a natively stopped OpenClaw gateway, restart it natively, and use a
genuinely changed user-initiated Telegram input. Hermes and all protected hosts
remain outside the mutation boundary.

## Dependencies

- AR-272 provides the Store-backed finalization service retained behind the
  adapter compatibility boundary.
- AR-277 provides the no-correction first-pass and terminal-rejection contract.
- ADR-0166 selects OpenClaw's awaited tool-result middleware for exact snapshot
  refresh while leaving Hermes and protected hosts unchanged.
- OpenClaw 2026.7.1-2 supplies the audited middleware, finalization, and
  full-payload hook contracts.

## Acceptance

- [x] Preserve the original Telegram transcript and correlated Store rows.
- [x] Prove exact `NO_REPLY` suppression occurs before Agency outbound hooks.
- [x] Add an expected-red for non-delivery and silent-sentinel guidance.
- [x] Make the smallest generated-prompt correction with no second model pass.
- [x] Keep OpenClaw native routing and all protected-host configuration untouched.
- [x] Preserve the second exact-text/no-outbound transcript and Store correlation.
- [x] Add expected-red coverage for full-envelope binding and native reset acknowledgement.
- [x] Defer only OpenClaw terminal commit until the complete outbound payload is bound.
- [x] Keep the native acknowledgement exception exact, one-use, session-bound, and expiring.
- [x] Run affected focused tests: 386 passed and 1 skipped.
- [x] Run affected focused tests and local documentation/lint gates.
- [x] Commit a clean substantive/ledger checkpoint before host mutation.
- [x] Install Agency only into stopped OpenClaw and restart it natively.
- [x] Preserve the third `NO_REPLY`/no-outbound transcript and exact Store/provider correlation.
- [x] Prove the native `/reset` hook race and keep its acknowledgement exception fail-closed.
- [x] Run affected reset-correlation suites: 218 passed.
- [x] Restore ordinary OpenClaw mode through a reversible native Agency disable.
- [x] Prove exact ordinary Telegram request/response delivery with Agency disabled.
- [x] Disprove terminal-tool delivery and identify the supported awaited tool-result seam.
- [x] Retain expected-red exit 232 and pass 72 focused OpenClaw tests.
- [x] Pass the proportionate header, Store, inference, registration, and policy gate: 289 passed, 2 skipped.
- [x] Install the OpenClaw-only snapshot candidate from a clean local checkpoint.
- [x] Preserve the fourth no-outbound transcript and exact finalization/model-receipt correlation.
- [x] Add expected-red coverage for post-authoring alias-only evidence mutation.
- [x] Keep the fix OpenClaw-only and preserve genuine resolved-model receipts.
- [ ] Deliver a genuinely changed fresh Telegram response with matching Store evidence.
- [ ] Preserve post-live Store integrity, launcher provenance, and config hashes.
- [ ] Tracker creation remains pending separate authorization.
