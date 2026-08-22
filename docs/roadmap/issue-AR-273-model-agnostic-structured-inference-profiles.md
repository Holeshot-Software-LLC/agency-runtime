---
title: "Make structured inference profiles model-agnostic"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [inference, litellm, structured-output, routing]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
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
blocks: [AR-119]
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

## Approach

Append the already bounded, deterministic JSON schema to the system
instruction for HTTP adapters that otherwise receive only JSON mode. Keep the
strict local validator authoritative and preserve response_format json_object
for compatibility with aliases whose eventual targets are unknown.

For LiteLLM chat-completions profiles, forward the configured thinking level
as the standardized reasoning_effort parameter and let LiteLLM translate it
for the routed provider and model. Do not construct a target-specific native
thinking object, inspect or rewrite the alias target, or change any host
configuration. Keep requested alias, model-group, and actual-model evidence
separate.

## Dependencies

- ADR-0153 named inference profiles and harness-scoped routing.
- ADR-0163 model-agnostic LiteLLM parameter translation.
- Existing bounded schema serialization and strict response validation.
- Existing OpenClaw live failure receipt retained as the regression evidence.

## Acceptance

- [x] A focused regression fails before repair because LiteLLM and generic OpenAI-compatible payloads omit the supplied schema.
- [x] A focused regression fails before repair because LiteLLM omits a configured reasoning effort.
- [x] The repaired payload includes the exact bounded schema instruction without weakening strict local validation.
- [x] LiteLLM receives reasoning_effort from thinking_level while the alias remains opaque and unchanged.
- [x] Codex OAuth/model/inference, Claude, ZCode, Anthropic, Ollama, and host-native inference configurations are unchanged; three separately authorized Codex MCP enablement flags are disabled.
- [x] Focused tests and proportionate local gates pass.
- [ ] The repaired Agency integration is installed into the existing OpenClaw host and a fresh live turn proves the required profile and alias.
- [ ] Tracker creation remains pending separate authorization.
