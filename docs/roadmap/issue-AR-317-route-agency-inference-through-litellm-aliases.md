---
title: "AR-317: Route Agency inference through LiteLLM aliases"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [litellm, inference, aliases, canary, configuration]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
  - docs/roadmap/issue-AR-316-size-ollama-selector-judge-context.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - README.md
  - CHANGELOG.md
  - docs/TROUBLESHOOTING.md
  - agency_runtime/core/canary_judge_provider.py
  - tests/test_canary_child_judge_provider.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-317
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-317: Route Agency inference through LiteLLM aliases

## Problem

The exact AR-297 production config sends generation, criticism, reranking, and
child-judge calls directly to Ollama while only embeddings use LiteLLM. That
binds operational configuration to backend model names and endpoints, so a
model change requires editing and reinstalling the Agency config. The direct
Ollama selector also caps a complete 19,520-token catalog at 8,192 tokens.

The operator requires every Agency inference stage on this Linux system to use
the existing authenticated local LiteLLM gateway and stable aliases. Ollama may
remain the private model backend, but it must not be an Agency-facing route.

## Current state

- The owner LiteLLM user service is active on `127.0.0.1:4000`. A secret-free
  mode-0600 snapshot under `ar297-litellm-routing-ioeoBe` records its current
  model definitions, readiness, and service state. Their SHA-256 prefixes are
  `39e2d4c1`, `a10d798c`, and `341fe8bb`; the existing fallback snapshot is
  `8e801fde`.
- `task-agency-router` currently resolves primarily to the local Qwen 14B
  abliterated model and has an existing shared general fallback chain. The
  operator selected the installed `mistral-small3.2:24b` model as its new
  primary backend.
- The exact config names direct Ollama models for generation, critic,
  reranker, and child judge. Its 4,096-dimensional `qwen3-embedding` route is
  already transported through LiteLLM.
- Canary child-judge pins admit exact CLI, Anthropic, and Ollama profiles but
  do not yet admit an authenticated `litellm` inference profile.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Admit one exact `litellm` inference profile as a canary child-judge pin only
when it declares a credential and uses HTTPS or a literal-loopback HTTP URL.
Retain the existing single-name resolution and replace the canary provider
tuple with that one profile, so Agency contributes no fallback.

Update `task-agency-router`'s primary deployment to Mistral without silently
removing its shared fallback policy. Create dedicated stage aliases for
generation, critic, reranker, embedding, and a no-fallback child judge. Give
the Mistral child alias a 32,768-token backend context so the complete catalog
fits, while preserving strict JSON, disabled thinking, and the bounded output
budget. Migrate the exact config to those aliases, the local LiteLLM endpoint,
and its credential environment name; disable direct Ollama routing.

## Dependencies

- ADR-0047 requires requested alias, router group, provider, and resolved model
  to remain separate evidence claims.
- ADR-0174 retains the direct Ollama product capability but no longer governs
  the selected AR-297 host topology.
- The operator approved LiteLLM-only Agency routing and a Mistral-backed
  `task-agency-router`; no Jina route is permitted.
- Existing shared LiteLLM fallbacks are foreign policy and remain unchanged
  unless the operator explicitly authorizes their removal.

## Acceptance

- [x] The operator selects LiteLLM aliases for every Agency inference stage
      and Mistral as `task-agency-router`'s primary backend.
- [x] A secret-free rollback snapshot captures the pre-change alias, fallback,
      readiness, service state, and exact-config fingerprint.
- [x] The canary admits one credential-declared safe LiteLLM profile; 158
      focused projection, inference-profile, network, and coverage-complete
      regressions pass warning-strict at exit 0.
- [ ] Stage aliases resolve to the approved local backends, preserve the 4,096
      embedding dimension, and give the no-fallback child judge enough context.
- [ ] The new mode-0600 exact config contains only LiteLLM inference routes and
      passes strict structural, model, credential, and installed validation.
- [ ] A fresh no-bypass Codex transaction proves one resolved Mistral child
      decision, v6 delivery/consumption, accepted finalization, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
