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

### Fifth Telegram failure: final hooks lose the preflight model identity

Clean pair `a9276e00` / `4b1172be` was installed as Agency-only operation
`175adc13-ef5f-4286-ac39-0a7584e9a982`. The gateway was natively stopped and
the installer did not restart it. Bundle `7a36d4df...`, runtime
`8ec95839...`, and launcher SHA `30c5760b...` bind to the checkout.
OpenClaw config changed only `meta.lastTouchedAt`; native model/provider,
channel, and credential configuration remained exact. Native restart loaded
ten hooks, the awaited middleware, no tool, and zero diagnostics; RPC plus
Telegram/Slack probes were green.

The new `/new` acknowledgement did not arrive. Exact `agency status`
nevertheless entered a new native session. Six `task-general` calls returned
HTTP 200, native tools completed, and the transcript contains one natural
1274-character response with the exact requested-alias/deterministic five-line
header. The kernel recorded `no queued reply payloads`; transcript SHA is
`deeb9040...`.

Trace `f946f532-4b53-4695-b660-36be48500dc3`, run
`79a11206-3c58-4ed0-b2b8-121bf3d0fdb9`, routing
`50c37f62-8278-4e35-99a2-7985b97cb4f9`, and terminal
`ae002770-f47f-4c84-890f-9ccfd37fd06b` correlate. Deterministic status
correctly used no workforce inference, specialist, skill, or resident binding.
The trace also has zero model receipts, proving the alias-only filter behaved as
designed. Finalization still rejected only `actual_model_selected`.

Installed-hook inspection then isolated the second causal mismatch. OpenClaw
supplies `modelId=task-general` in `before_prompt_build`, which Agency used
to author the header, but omits `modelId` in `before_agent_finalize` and
final payload context. Final validation therefore compared the requested-alias
header against `none observed`.

Expected-red exit 17 models that exact context loss. The generated OpenClaw
plugin now stores the bounded preflight model beside its existing session/run
context, reuses it for pre-verify and outbound revalidation, and deletes it at
the final payload gate. Existing TTL, maximum-entry, byte-bound, and
runtime-disable clearing controls remain authoritative. The focused OpenClaw
adapter, security, registration, and native-installer slice is 90 passed and 1
skipped. No shared policy, other adapter, OpenClaw source/configuration, model
routing, direct send, rewrite, or correction pass changed.


### Sixth Telegram turn: installed correlation repair delivers

Clean pair `71cb0975` / `a518ed23` was installed as Agency-only operation
`c3b124d6-6a88-46b4-8c5a-706c5187457b` while OpenClaw was natively stopped.
The installer left it stopped. Bundle `fcc48773...`, runtime `0b05a499...`,
and launcher SHA `317045e7...` bind to that checkout. Native restart loaded
ten hooks, the awaited middleware, no Agency tool, and zero diagnostics.
Gateway RPC plus Telegram/Slack probes were green.

The current OpenClaw config differs from exact pre-install SHA `0f30f12d...`
only at `meta.lastTouchedAt`; native `litellm/task-general`, all six
fallbacks, providers, channels, and credential indirection remain identical.
The gateway process has populated `LITELLM_API_KEY`; no value was emitted.

A sixth fresh exact `agency status` turn entered native session
`5570abb9-eecc-4d77-be4b-bb9636bdf886`. Trace
`78a68fdc-e192-4098-b8c7-58d20cf3bd8a`, run
`6f446944-da85-4eda-8049-227bf268775e`, deterministic routing
`da98bac1-c78a-4be7-9a6b-a121386fdaf7`, and terminal
`9398965e-550c-452d-9f85-3e59f2ecd029` correlate. The run completed,
finalization accepted with no missing fields, and Telegram recorded outbound
after inbound.

The 489-character first response has SHA `1e8c1df5...`; native transcript SHA
is `593ddef8...`. Its exact header records `agency-steward`, no delegation, no
skill, `requested execution alias: task-general`, and deterministic
recruitment. `task-general` is the OpenClaw parent request alias for this
control turn. Zero Agency model receipts, specialists, skills, and resident
bindings prove deterministic status did not invoke `task-agency-router`.
Neither requested alias is promoted into an answering-model claim.

Pre-install Store backup SHA `d00c86f9...` and post-status SHA `470aa2fd...`
both have integrity `ok`, schema 47; contractors remain 15. The AR-278
delivery defect now passes in its exact scope. Skill loading and substantive
Agency workforce inference remain separate pending proofs.

### Post-status skill turn: alias passes, middleware correlation fails

A genuinely new read-only request in the same native session produced trace
`6b18f9f0-a8bb-4a68-b70b-45ec7cdfe454`, completed run
`afc905ca-f68b-40c7-b694-b1842e7277c7`, accepted routing
`26492374-3d54-4da2-8bc6-0381e83813f4`, specialist
`5b2f0fbd-445d-41f5-9d4c-1e2a99f3ff09`, and accepted terminal
`d6ae9ade-b124-46b5-8822-7457a177f526`. Telegram outbound followed inbound.

Three wrapper receipts requested exact alias/model-group
`task-agency-router` through OpenClaw profile `linux-task-agency-router` and
provider type `litellm`; routing records `fallback_applied=false`. The native
parent separately remained LiteLLM `task-general`. No provider telemetry named
an actual answering model, so neither alias is promoted into that claim.

OpenClaw read the exact eligible `healthcheck` `SKILL.md` reported by native
inventory, but Store skill count remained zero and the exact final header said
`Skills loaded: none`. This is retained failed skill evidence. Installed source
shows why: OpenClaw's awaited middleware supplies tool arguments but its runtime
factory supplies no session/run correlation to the middleware callback. The
generated Agency test had incorrectly invented that context, so the live bridge
failed closed with empty identities.

Expected-red exit 245 now matches the installed callback. The OpenClaw-only
repair records bounded, expiring, one-use correlation by `toolCallId` in
`before_tool_call`, consumes it in the awaited result middleware, rejects
ambiguous collisions, and clears state when Agency is disabled. The affected
installer, dispatch, inference, final-header, and Store slice is 374 passed with
1 skipped.

Agency-only install `251c4349-f7e3-4640-980d-055b857c0abe` installed that
repair from clean checkout `c0426ab9` while OpenClaw was natively stopped, and
the installer left it stopped. Native restart is RPC-green and loaded 11 hooks,
including `before_tool_call`, with no Agency tool or plugin diagnostic. Runtime
digest `70239e65...` and launcher SHA `3090708c...` bind to this checkout.
OpenClaw's native `litellm/task-general` primary and six fallbacks are unchanged;
its only semantic config delta is `meta.lastTouchedAt`, and Agency config SHA
`43367ec9...` is unchanged. A later `/new` established native session
`b815780c-23fb-4fdb-8731-aed6d162b769`; its exact first `agency status` turn
completed as trace `7f4aa31c-9d93-4199-bac0-b5818cea91de`, finalization
`6ce7c157-98fd-4ab7-aabc-d4722e02a43b` accepted with no missing fields, and
Telegram outbound followed inbound. The response SHA is `a4c784dc...` and the
preserved transcript SHA is `a2ec1af7...`. Deterministic control correctly made
no Agency inference claim.

OpenClaw later rolled native session `31983848-8d75-4e8f-ae11-8b8087d8c429`.
Its genuinely changed `tmux` request completed as trace
`adff32ff-bbd0-4afd-befd-e5c647ac76fc`, finalization
`3d5bdb26-881d-4759-9ded-2ae2ac167a44` accepted, and Telegram delivered. The
exact header and Store row both name `tmux`. All three wrapper receipts used
profile `linux-task-agency-router`, provider type `litellm`, and exact
alias/model-group `task-agency-router` with zero fallback. Actual answering
model telemetry remains unavailable. The exact substantive proof remains
pending; Hermes, Codex, Claude, and ZCode remain untouched.

The exact substantive restart-safety request then completed as trace
`5ba0b638-9db8-4144-8be0-2d9b17f6b51d`, run
`ad2b1238-dd8f-49c9-9b30-2107baf7b499`, accepted routing
`b5f22f42-4ddf-4a8b-85ed-8fb56c13e7b1`, and accepted terminal
`5eb2e7fa-ff50-4728-b7d2-d6a497ff57b5`. All three provider attempts used
OpenClaw profile `linux-task-agency-router`, provider type `litellm`, and exact
alias/model-group `task-agency-router`; fallback count is zero. The exact header
records two loaded specialists, no delegation, and `openclaw-operations` with
matching Store row. No delegation or native-child rows exist. Telegram
delivered two chunks. Final Store integrity is `ok`, schema 47; contractor,
config, and launcher invariants hold. Actual answering model remains unavailable.

### Seventh Telegram failure: native reset acknowledgement omits session context

Clean repair/ledger pair `21f2519d` / `f86bedb4` was installed into natively
stopped OpenClaw as Agency-only install
`776616e9-c086-4078-a9c3-b0875a5e6ebc`; the installer left the gateway
stopped. Native restart was RPC-green, native `litellm/task-general` plus all
six fallbacks remained unchanged, and Hermes stayed active and unmodified.

The next exact `/new` reset created fresh native session
`241cbd97-ff10-49b8-b4bb-2458cb9c8937`, but no acknowledgement was delivered
and no Agency run followed. OpenClaw's supported `message_sending` callback can
omit its optional `sessionKey` when the native acknowledgement has no attached
outbound session. Agency's installed acknowledgement gate required that field,
so it timed out and canceled the valid exact acknowledgement.

The live-shaped regression first failed with that installed callback shape.
The bounded repair retains the hashed-session path when context exists. Without
session context it can consume only one recent authorization whose fixed
expected text exactly matches; zero or multiple candidates fail closed. Replay,
wrong text, missing reset, and expiry remain rejected. The OpenClaw security,
adapter, streaming, and installer slice passed 245 tests with 1 intentional
skip. Clean pair `d4d4b829` / `99b1380d` was then installed Agency-only as
`5e1a074e-81a6-4fdf-a464-937c66d9b400`; bundle `b0010f67...`, runtime
`ebbf13cd...`, and launcher SHA `7f393f2a...` bind to the checkout. The
installer left OpenClaw stopped. Native restart became RPC-green with zero
restarts; native `litellm/task-general`, all six fallbacks, and Agency routing
remained unchanged. Hermes stayed active and unmodified.

The operator sent a changed exact `/new`. OpenClaw reset native state into
session `1b4c7016-cac1-4aca-8639-075038d5b982`, but again no acknowledgement
was delivered and no Agency run followed. Native log event SHA `e66fb292...`
records the caught Codex harness reset warning; redacted failure artifact SHA
is `22f88b59...`. The first repair was therefore necessary but insufficient.

Installed flow inspection isolated the missed layer: OpenClaw sends the native
reply through `reply_payload_sending` before `message_sending`. Agency had
added correlation only to the latter, so the earlier final-only gate canceled
the exact acknowledgement before it could be consumed. A two-gate regression
failed before implementation at exit 30. The smallest repair makes the
reply-payload gate wait for and verify—but not consume—the same exact bounded
authorization; the message gate remains the one-use consumer. Replay and
concurrent ambiguity still fail closed. The affected slice is 246 passed with
1 intentional skip.

Clean two-gate pair `3e71247a` / `ff1e9594` was then installed Agency-only
into natively stopped OpenClaw as
`711f3174-88b1-4b9a-948d-a47f316e6744`; the installer left it stopped.
Bundle `d1a5ef80...`, runtime `70328489...`, and launcher SHA `ae41c0be...`
bind to that checkout. Native restart became RPC-green, Telegram's credential
probe passed, OpenClaw retained `litellm/task-general` plus all six fallbacks,
and Hermes remained active and unmodified.

The changed `/new` completed native ingress and reset into session
`25ed26a0-8dc8-433d-9bc1-3afdbe503ffd`, but again produced no acknowledgement,
outbound receipt, or Agency run; the operator confirmed non-delivery. Native
log/command event SHAs are `716f2bd1...` / `c8b214cf...`; redacted failure
artifact SHA is `ea9d4c9e...`. The static two-gate flow therefore remains
necessary but is not a complete model of live callback ordering.

The next bounded diagnostic records only hook phase, boolean state, text-surface
count, content length, and authorization count. It never records message text,
session or channel identifiers, credentials, or payloads. Its regression also
asserts those exclusions. The affected slice remains 246 passed with 1
intentional skip. An initial ambient-umask run retained 66 namespace-trust
failures, 180 passes, and 1 skip; changing only the documented test-process
umask to `0077` produced the green result. This diagnostic candidate is not
installed in that evidence state.

Clean diagnostic pair `675fb22a` / `b8c3b155` was subsequently installed
Agency-only into natively stopped OpenClaw as
`2949e798-5500-45c9-956b-4b5a97aa802b`; the installer left the gateway
stopped. Bundle `72c40ad4...`, runtime `fb719841...`, and launcher SHA
`859139b0...` bind to the checkout. Native restart is RPC-green with zero
restarts, all 11 required hooks registered, and Telegram configured, running,
and probe-green. OpenClaw retains `litellm/task-general` plus the same six
fallbacks; Hermes remains active and unmodified. Online Store backup SHA
`5ca1ffbe...` has source/backup integrity `ok`, schema 47, and contractors
remain 15.

The unavailable system `sqlite3` binary and a mistaken SQL table name are
retained as failed backup attempts; neither mutated the Store. Python's SQLite
backup API then completed the required WAL-consistent backup, and contractor
count came from the checkout CLI. A literal `~/` config-path hash failure is
also retained; normalizing that native path produced pre/post OpenClaw config
SHAs `562c0c4e...` / `cfdacc1d...`. No credential value was emitted.

The operator then sent the changed `/new` and again received no
acknowledgement. The diagnostic proved the exact live sequence without
retaining content or identifiers: `reply_payload_sending` observed the exact
final acknowledgement with a session but no authorization; 2 ms later
`before_reset` created one authorization under another present lifecycle
session; the waiting reply gate still found no exact-key authorization after
one second and canceled. No OpenClaw Agency run or routing decision followed.
Redacted artifact SHA is `0fe6ae7a...`.

The new live-shaped regression uses distinct pre-reset, post-reset, and final
delivery sessions and failed before implementation at exit 30. The smallest
repair preserves exact-session priority, then permits the already-established
unique recent exact-text fallback when a supplied lifecycle session does not
match. Zero or multiple candidates, wrong text, expiry, and replay still fail
closed; a new mismatched-session ambiguity assertion proves the two-candidate
case. The affected slice is 246 passed / 1 intentional skip. The candidate is
not installed.

## Approach

Change only Agency's OpenClaw adapter as specified by ADR-0166. Do not expose
the finalizer tool. Supply the initial exact Store-backed header at preflight,
record native tool evidence through OpenClaw's awaited tool-result middleware,
and append the updated exact snapshot before the model continues. Keep
`before_agent_finalize` as the first-pass validator and the last reply-payload
gate as the complete-envelope commit and authorization boundary.

Retain exact reset acknowledgement correlation: bind to the session when the
supported callback supplies it, otherwise require one recent exact unambiguous
authorization. Do not add a model revision, rewrite an invalid natural response,
send directly, alter OpenClaw source or configuration, change native or Agency
inference routing, or weaken the Store-backed outbound seal. From a clean
checkpoint, install Agency Runtime only into a natively stopped OpenClaw gateway,
restart it natively, and use a genuinely changed user-initiated Telegram input.
Hermes and all protected hosts remain outside the mutation boundary.

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
- [x] Preserve the fifth no-outbound transcript and zero-model-receipt correlation.
- [x] Add expected-red coverage for final-hook model identity loss.
- [x] Carry bounded preflight model identity through both OpenClaw final gates.
- [x] Deliver a genuinely changed fresh Telegram response with matching Store evidence.
- [x] Preserve post-live Store integrity, launcher provenance, and config hashes.
- [x] Preserve the delivered post-status workforce turn and its failed native-skill evidence without claiming success.
- [x] Add installed-contract expected-red coverage for absent middleware correlation and a bounded collision-safe repair.
- [x] Install the correlation candidate through Agency-only install while OpenClaw is natively stopped.
- [x] Prove a genuinely different native skill plus the exact substantive restart-safety review.
- [x] Preserve the sessionless post-reset acknowledgement failure and add exact ambiguity/replay regression coverage.
- [x] Install the sessionless acknowledgement repair and preserve the independent earlier-gate failure.
- [x] Add expected-red coverage for the complete reply-payload/message-sending path.
- [x] Install the two-gate acknowledgement repair and preserve its independent live non-delivery.
- [x] Add bounded content-free phase diagnostics with explicit sensitive-content exclusions.
- [x] Install the diagnostic checkpoint with Store/config/launcher provenance.
- [x] Preserve the fourth non-delivery and its content-free live phase trace.
- [x] Add expected-red coverage for differing reset-lifecycle sessions and a bounded repair.
- [ ] Install the exact traced repair and prove one fresh `/new` acknowledgement.
- [ ] Apply the exact traced repair and prove a fresh `/new` acknowledgement.
- [ ] Tracker creation remains pending separate authorization.
