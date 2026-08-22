---
title: "Make structured inference profiles model-agnostic"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-22
tags: [inference, litellm, structured-output, routing]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/inference_profiles.py
  - tests/test_roster_inference_adapter.py
  - tests/test_inference_profiles.py
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-273
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119, AR-275]
---

# AR-273: Make structured inference profiles model-agnostic

## Problem

Agency's named inference profiles correctly separate adapter, requested
model or alias, endpoint, credential indirection, and thinking level. The
generic OpenAI-compatible HTTP payload does not complete that abstraction:
it requests a JSON object but does not supply the bounded response schema to
the model, and the LiteLLM path records a configured thinking level without
forwarding it.

This makes strict structured inference depend on whatever model happens to
sit behind an alias. It also contradicts the operator requirement that a
LiteLLM alias can be retargeted later without changing Agency code or host
configuration.

## Current state

Fresh OpenClaw trace 9384d3a3-0a28-4150-a8fa-ab493efda7bf and run
a5504721-0aa9-4fa3-98df-f5667c933b5b selected the OpenClaw harness
automatically, resolved profile linux-task-agency-router, attempted provider
type litellm, and requested model group task-agency-router twice. Both
attempts ended provider_response_contract_invalid with no fallback, no
specialist load, and no finalization. The alias target, native OpenClaw model,
endpoint, and credential indirection are not the defect and remain unchanged.

The transport sends response_format type json_object while its system prompt
only says to match a supplied schema; the schema is never included on the
LiteLLM or generic OpenAI-compatible path. It also omits the profile's
reasoning effort for LiteLLM even though the receipt reports the level as
consumed.

The initial repair's trace `517c2c78-95e6-4dea-bfd7-b43f6d48671a`
selected the intended OpenClaw profile, LiteLLM provider, and exact
alias/model-group with zero fallback. Its HTTP-200
`provider_no_valid_response` turn remains an OpenClaw 180-second timeout.
The owner-approved content-free diagnostic reused the populated credential only
in process memory and emitted no content or secret. It returned HTTP 200 with a
normal OpenAI response envelope and braced JSON content, but that content had
four keys where the closed two-key diagnostic schema allowed no extras. This
isolates the remaining defect to prompt-only schema enforcement.

Exact-schema commit `fba12371` and ledger `6ad46fb4` are installed into the
existing stopped OpenClaw host as Agency install
`b526ecdc-a538-4797-a8e8-656ecb3b315b`, bundle
`94d87723b900387f9dbad0dda73613b449332c34683a4fd68674c0e354314a22`,
and runtime digest
`71c917a91ed3527065447e6aa5ec4e36466d1710f7f5d0a41411a5ac585decda`.
The installer left the gateway stopped; the same native service restarted
RPC-green with the plugin loaded and Telegram/Slack probe-green. OpenClaw's
only semantic config delta is `/meta/lastTouchedAt`; protected configuration
hashes remain unchanged. Fresh live response proof remains open.

Post-install exact first-message status session
`fe3ab39c-fea0-4974-82b2-c85478b10b8a` completed with Store trace
`3b26c907-2c9d-4240-8160-8c6d7cce6a08`, accepted finalization
`97eaacb8-9dcf-4431-8150-0e1d702e8ce3`, and a hash-matched native response.
Its deterministic abstention proves activation and delivery only; exact-schema
workforce inference remains for a non-control turn.

The next genuinely new work unit produced completed trace
`402e37f5-f38e-425b-95c6-62e911be2566` and Store run
`4963f31f-e114-4fa0-b051-8ded1ded51a1`. All three structured provider stages
automatically selected OpenClaw profile `linux-task-agency-router`, provider
type `litellm`, and exact requested alias/model-group `task-agency-router`;
each was applied with a valid structured response. Routing decision
`982f6c68-ac38-41a3-a84a-b7b60bee39cb` accepted and finalization
`cfb2e3de-9a2b-4fda-9194-6edcb52ca3a5` delivered a response whose SHA-256
`7c785b301b68e65a42c6a69f01537821a398bca2d7a238c598a75890f2b8c2f5`
matches the native transcript. No Codex, Claude, or alternate provider identity
appears; wrapper receipts do not supply an actual answering model, so none is
claimed.

This proves the exact-schema LiteLLM repair for a live workforce turn. It does
not prove skill loading: OpenClaw used native `read` for the bundled Weather
`SKILL.md`, while Agency recorded no skill row and honestly finalized
`Skills loaded: none`. AR-274 owns that separate bridge-normalization defect.

A later exact restart-safety review in fresh session
`7e1f8a3c-6b29-4ea0-b1d4-93a4c51de287` retained the opposite eval outcome:
trace `869ef22a-e1a5-4b7e-b024-6bf12aa371ea` rejected two planner responses as
`provider_response_contract_invalid` with no fallback. OpenClaw then entered a
553809-byte tool loop, hit native context overflow, and the Gateway timed out
after 630000 ms. The CLI's separately identified embedded fallback is not
Agency evidence. This retained failure does not change the earlier live pass,
the opaque alias target, strict validator, or protected-host configuration.


Smaller changed-input session `9a61c4e7-2fd8-40bc-a5f0-3e71b2c94d66`
confirmed the same blocker without timing out: trace
`b325368f-22e2-4815-8d01-2e9d1c22c543` rejected two planner responses from
the exact profile and alias with zero fallback; receipt
`fe0c2f6b-e9be-45a6-b15a-f450c7e8a154` records `inference_invalid`. Its
unheaded native answer has no routing or finalization row and is not Agency
delivery. This is a retained eval failure, not authority to change the alias
target or weaken the strict validator.

## Approach

Append the already bounded, deterministic JSON schema to the system
instruction for HTTP adapters that otherwise receive only JSON mode. For the
LiteLLM adapter, also send the exact schema through the standard JSON-schema
response format and let LiteLLM translate it for the opaque routed target.
Keep the strict local validator authoritative.

For LiteLLM chat-completions profiles, forward the configured thinking level
as the standardized reasoning_effort parameter and let LiteLLM translate it
for the routed provider and model. Do not construct a target-specific native
thinking object, inspect or rewrite the alias target, or change any host
configuration. Keep requested alias, model-group, and actual-model evidence
separate.

## Dependencies

- ADR-0153 named inference profiles and harness-scoped routing.
- ADR-0163 model-agnostic LiteLLM parameter translation, as superseded by
  ADR-0164 for exact schema delivery.
- Existing bounded schema serialization and strict response validation.
- Existing OpenClaw live failure receipt retained as the regression evidence.

## Acceptance

- [x] A focused regression fails before repair because LiteLLM and generic OpenAI-compatible payloads omit the supplied schema.
- [x] A focused regression fails before repair because LiteLLM omits a configured reasoning effort.
- [x] The repaired payload includes the exact bounded schema instruction without weakening strict local validation.
- [x] LiteLLM receives reasoning_effort from thinking_level while the alias remains opaque and unchanged.
- [x] A content-free live diagnostic proves endpoint, credential, alias, and response envelope are healthy while prompt-only output violates a closed schema.
- [x] LiteLLM receives the exact closed schema through its standardized JSON-schema request without target inspection or alias changes.
- [x] Codex OAuth/model/inference, Claude, ZCode, Anthropic, Ollama, and host-native inference configurations are unchanged; three separately authorized Codex MCP enablement flags are disabled.
- [x] Focused tests and proportionate local gates pass.
- [x] The repaired Agency integration is installed into the existing OpenClaw host.
- [x] The LiteLLM JSON-schema repair is installed into the existing OpenClaw host.
- [x] A fresh exact-status control reaches Store-backed finalization and native response delivery after installation.
- [x] A fresh live attempt proves the required OpenClaw profile, LiteLLM provider, exact alias/model-group, and zero protected-provider fallback.
- [x] A fresh live turn returns a valid planner object and reaches strict finalization.
- [ ] Tracker creation remains pending separate authorization.
