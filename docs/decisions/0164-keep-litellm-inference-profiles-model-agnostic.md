---
title: "Keep LiteLLM inference profiles model-agnostic"
status: superseded
category: decisions
created: 2026-08-21
updated: 2026-08-21
tags: [inference, litellm, routing, structured-output]
related:
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0165-delegate-exact-schema-translation-to-litellm.md
  - docs/roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/inference_profiles.py
  - tests/test_roster_inference_adapter.py
  - tests/test_inference_profiles.py
supersedes: []
superseded_by: docs/decisions/0165-delegate-exact-schema-translation-to-litellm.md
id: ADR-0164
type: decision
deciders: [maintainers]
---

# ADR-0164: Keep LiteLLM inference profiles model-agnostic

## Context

ADR-0153 made adapter, model, thinking level, endpoint, and credential source
profile data so an operator can retarget inference without changing runtime
code. Its original LiteLLM mapping described a provider-native thinking
object. That shape requires Agency to know which provider and model sit behind
an alias, defeating the abstraction when the alias target changes.

The OpenAI-compatible LiteLLM chat-completions contract accepts
reasoning_effort and translates it for supported routed providers and models.
The same gateway supports native structured-output parameters unevenly across
models. An alias does not give Agency stable capability knowledge about its
future target.

## Decision

For adapter litellm, Agency forwards a configured profile thinking_level as
the standardized reasoning_effort chat-completions parameter. LiteLLM, not
Agency, owns translation to the routed provider's native reasoning controls.
Agency never derives a provider-native thinking object from an opaque alias.

For structured chat-completions calls, Agency includes its exact bounded JSON
schema in the trusted system instruction and retains JSON-object response mode.
The runtime continues to validate the returned object against its closed local
contract. Native JSON-schema enforcement may be added later only behind
capability evidence that remains valid for an alias target.

Requested alias and model-group evidence remain the configured LiteLLM name.
Agency records an actual answering model only when provider telemetry supplies
it. A provider rejection, invalid response, or timeout remains a failed
attempt; it does not authorize fallback to a protected host or a rewrite of
the alias target.

## Consequences

- Operators can retarget a LiteLLM alias for evaluation without changing
  Agency or host configuration.
- Reasoning levels remain one profile field across LiteLLM targets; unsupported
  target behavior is surfaced as provider evidence rather than guessed.
- Prompt-level schema delivery works across more routed models than assuming
  native JSON-schema support, while strict local validation remains the safety
  boundary.
- The alias is never promoted into an actual-model claim.
- Direct Anthropic, Ollama, OpenAI-compatible, and CLI adapter policies remain
  unchanged except that compatible HTTP paths receive the same explicit schema
  instruction.

## Alternatives

- Construct a native thinking object in Agency. Rejected because it couples an
  opaque alias to a provider/model-specific request shape.
- Send native JSON-schema response_format unconditionally. Rejected because a
  future alias target may not support it and Agency cannot infer that capability
  from the alias.
- Change task-agency-router to a model known to satisfy the current prompt.
  Rejected because the alias target is operator-owned evaluation policy, not an
  Agency implementation detail.
