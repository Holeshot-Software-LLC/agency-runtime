---
title: "Delegate exact schema translation to LiteLLM"
status: accepted
category: decisions
created: 2026-08-21
updated: 2026-08-21
tags: [inference, litellm, routing, structured-output]
related:
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - agency_runtime/core/structured_provider.py
  - tests/test_roster_inference_adapter.py
supersedes:
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
superseded_by: null
id: ADR-0164
type: decision
deciders: [maintainers]
---

# ADR-0164: Delegate exact schema translation to LiteLLM

## Context

ADR-0163 kept LiteLLM requests in JSON-object mode because an opaque alias does
not expose stable target capabilities. A bounded live diagnostic then proved
that transport, authentication, alias resolution, and the OpenAI response
envelope were healthy, but prompt-only schema delivery was insufficient: the
answer was valid JSON with four keys where Agency's closed diagnostic contract
allowed exactly two.

The installed LiteLLM adapter treats the OpenAI-standard
`response_format.type=json_schema` as a router-level contract. For the current
routed provider it translates the supplied schema into that provider's native
format. This preserves the alias boundary because Agency does not identify or
configure the target.

## Decision

For adapter `litellm`, Agency sends the exact bounded local schema through the
standard chat-completions JSON-schema response format with a deterministic
name and `strict=true`. Agency also retains the exact schema in its trusted
system instruction.

LiteLLM owns provider- and model-specific translation. Agency does not inspect
the alias target, branch on a target model, remap the alias, or construct a
provider-native schema object. Direct OpenAI-compatible, Anthropic, Ollama, and
CLI adapter behavior remains unchanged.

Strict local parsing and schema validation remain authoritative. A target that
rejects, drops, or fails to satisfy the structured-output request produces a
failed provider attempt; it does not authorize relaxed validation, protected
provider fallback, or an actual-model claim. ADR-0163's standardized
`reasoning_effort` translation and alias-evidence rules remain in force.

## Consequences

- An operator can retarget the LiteLLM alias without changing Agency or host
  configuration; LiteLLM owns capability translation for the selected target.
- Models that honor LiteLLM's structured-output contract receive the exact
  closed Agency schema rather than only a prompt description.
- Prompt instruction plus provider enforcement is defense in depth; strict
  local validation remains the final safety boundary.
- Unsupported future targets fail visibly and without protected-provider
  fallback instead of weakening the contract.
- The requested alias/model-group remains distinct from an actual answering
  model supplied by provider telemetry.

## Alternatives

- Keep JSON-object mode and add more prompt wording. Rejected because the live
  response was valid JSON that still violated a small closed schema.
- Infer the alias target and send its native schema shape. Rejected because it
  couples Agency to operator-owned routing and breaks retargetability.
- Accept or discard extra response fields. Rejected because that weakens the
  closed contract and can hide model noncompliance.
- Change the alias target. Rejected because target selection is operator-owned
  evaluation policy and was not the transport defect.
