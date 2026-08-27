---
title: "Use LiteLLM aliases as the host inference control plane"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [litellm, inference, aliases, operations, canary]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - README.md
  - CHANGELOG.md
  - docs/TROUBLESHOOTING.md
  - agency_runtime/core/canary_judge_provider.py
  - tests/test_canary_child_judge_provider.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0181
type: decision
deciders: [maintainers]
---

# ADR-0181: Use LiteLLM aliases as the host inference control plane

## Context

AR-297 initially bound most local stages directly to Ollama model names. Its
second exact Codex attempt reached the approved Mistral child judge but the
direct selector request capped a 19,520-token complete catalog at 8,192 tokens.
Raising that hardcoded request cap would repair this one transport while still
requiring Agency config changes whenever the operator changes a backend model.

This Linux host already runs an authenticated owner LiteLLM gateway. The
operator requires all Agency inference to traverse that gateway through stable
aliases and specifically selected Mistral as `task-agency-router`'s primary
backend. The gateway's existing router alias also carries shared fallbacks that
must not be silently removed as part of a production proof.

## Decision

On this host, Agency structured generation, criticism, reranking, embedding,
legacy selection, and canary child-judge calls use authenticated stage-specific
LiteLLM aliases at the literal-loopback gateway. Ollama remains an internal
LiteLLM backend and is disabled as a direct Agency route. Jina is neither
configured nor called.

Change `task-agency-router`'s primary deployment to the installed local
`mistral-small3.2:24b` backend while preserving its pre-existing shared fallback
policy. Exact canary evidence uses a separate Mistral-backed
`task-agency-child-judge` alias with no gateway fallback and a 32,768-token
backend context. Generation, critic, reranker, and 4,096-dimensional embedding
routes receive independent aliases so the operator can change one stage
without reinstalling Agency or coupling unrelated stages.

A canary may project a `litellm` profile only when it resolves exactly once,
declares a credential, and uses HTTPS or literal-loopback HTTP. Agency narrows
the canary to that one provider and never borrows an ordinary provider chain.
Alias text is not model proof: ADR-0047's response and callback evidence must
identify the actual provider/model used by every successful proof.

## Consequences

The owner can change backend deployments centrally while the installed Agency
config and host integrations retain stable route identities. The LiteLLM
gateway, its credential projection, per-alias context, readiness, and actual
model telemetry become production dependencies and must be proven in clean
containers and later ordinary processes.

The shared `task-agency-router` fallback chain remains available to its other
consumers. AR-297's child proof cannot traverse it because its dedicated alias
has no fallback. Missing credentials, unsafe endpoints, unavailable aliases,
ambiguous resolution, gateway failure, or absent actual-model evidence fail
closed. The embedding width, strict assurance, additive dense recall, thinking
levels, and stage independence remain configuration invariants.

## Alternatives

Raising only the direct Ollama selector context to 32,768 was rejected by the
operator because it preserves backend names in Agency configuration. Reusing
the shared router alias for exact child proof was rejected because its fallback
chain cannot prove a free Mistral-only decision. Removing that shared fallback
chain was rejected without explicit authority because it is existing host
policy used outside this bounded install. Keeping LiteLLM only for embeddings
was rejected because it does not provide the requested central control plane.
