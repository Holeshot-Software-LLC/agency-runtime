---
title: "Reconcile LiteLLM actual-model and router evidence separately"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-16
tags: [litellm, models, routing, receipts, observability]
related:
  - docs/roadmap/issue-AR-29-reconcile-litellm-model-and-router-evidence.md
  - docs/roadmap/issue-AR-64-reject-unproven-litellm-router-alias-echoes.md
  - docs/roadmap/issue-AR-78-preserve-litellm-router-when-model-is-unavailable.md
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0047
type: decision
deciders: []
---

# ADR-0047: Reconcile LiteLLM actual-model and router evidence separately

## Context

LiteLLM can accept a stable model group while routing each request to a
different provider deployment. Its current standard logging contract exposes
the group as `model_group`, the provider-bound routed name as
`hidden_params.litellm_model_name`, and the successful provider response model
as `response.model`. These values answer different questions and cannot be
collapsed safely. A requested alias or opaque deployment `model_id` is not proof
of what ran.

Older SDK and Proxy versions expose only parts of that contract. The runtime
must preserve compatibility without filling missing truth with guesses.

## Decision

Persist the requested model, LiteLLM router group, resolved provider, and
resolved model as separate bounded receipt fields. Reconcile a successful
actual model in this strict order:

1. provider-reported `response.model`;
2. StandardLoggingPayload `hidden_params.litellm_model_name`, followed by the
   equivalent legacy response-hidden field;
3. a fixed allowlist of bounded deployment metadata: `deployment`,
   `deployment_model_name`, and configured `model_info.base_model`.

Resolve a missing provider only from provider-qualified values, LiteLLM's
explicit `custom_llm_provider`, or the sanitized deployment endpoint. Never use
the requested alias or opaque `model_id` to infer actual execution. Retain
`model_id` as operational metadata only.

Keep the router group even when its text matches a resolved model; equality does
not erase its distinct role. Render successful LiteLLM evidence as
`requested -> provider/model via LiteLLM router group`. If no authoritative
actual model exists, including when a response only echoes the requested or
group alias, record unavailable. Failed calls always record unavailable
regardless of success-shaped response fields.

A LiteLLM success or failure callback terminates a provider request, not the
Agency turn. It may persist the receipt and discard request-only in-memory
routing context, but it must not close the correlated run. Stop or central
finalization owns terminal turn state after validating the complete evidence
graph.

When a trace has multiple model receipts, choose the completion receipt by
evidence quality before chronology: successful concrete model telemetry outranks
unavailable or failed observations, and direct LiteLLM/host telemetry outranks
wrapper/unknown evidence at equal quality. Use database ingestion order only to
break ties within the same quality and authority class.

Treat receipt provenance as an ingestion-path property, not caller-supplied
metadata. The generic Store and public runtime APIs normalize source=litellm to
unknown; only the installed LiteLLM callback's dedicated internal recorder may
persist the authoritative LiteLLM source. At the same Store boundary, validate
correlation identifiers, bound every receipt field and fallback count,
canonicalize provider tokens, reject control-bearing or custom provider aliases,
and sanitize endpoints before SQLite persistence.

## Consequences

- Headers and dashboard receipts distinguish the user's requested alias, the
  LiteLLM routing group, and the provider/model that actually ran.
- Disagreement is deterministic and favors provider response telemetry.
- Existing LiteLLM installations without StandardLoggingPayload continue to
  work when they expose response or legacy hidden telemetry.
- Telemetry-poor installations remain visibly unavailable rather than appearing
  successfully reconciled.
- Opaque deployment identifiers remain useful for operations without becoming
  model claims.
- Model-call completion cannot manufacture a terminal-correlation loop before
  Agency response finalization.
- A late low-fidelity observation cannot erase stronger actual-model and router
  evidence from the same turn.
- Public or generic receipt writers cannot gain LiteLLM authority by spoofing a
  source label, and malformed provider metadata cannot reach headers or
  operator surfaces.

## Alternatives

- Treat `model_group` as the actual model. Rejected because a router group can
  select multiple deployments.
- Infer from `model_id`. Rejected because LiteLLM deployments commonly use UUIDs
  or operator-defined opaque identifiers.
- Fall back to the requested model. Rejected because aliases are intentionally
  decoupled from provider execution.
- Overwrite the router group with the resolved model. Rejected because it loses
  the routing decision needed to explain and operate the system.
