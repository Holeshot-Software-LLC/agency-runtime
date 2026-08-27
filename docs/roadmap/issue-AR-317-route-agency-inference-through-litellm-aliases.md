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
- The prior exact config named direct Ollama models for generation, critic,
  reranker, and child judge. It remains immutable as historical evidence and
  has been superseded for the next candidate by a new LiteLLM-only artifact.
- Canary child-judge pins admit exact CLI, Anthropic, and Ollama profiles but
  now also admit one authenticated safe `litellm` profile after 158 focused
  warning-strict tests.
- `task-agency-router` now resolves primarily to Mistral with a 32,768-token
  context. Its existing fallback snapshot remains byte-identical at
  `8e801fde...075f`. Five dedicated stage aliases resolve to the approved local
  backends and each returns HTTP 404 for general-fallback lookup; the canonical
  model snapshot is `6a80b30a...be8df`.
- A 20,050-token child-alias probe returns strict JSON at HTTP 200 with zero
  attempted fallbacks. Ollama records `n_ctx=32768`, all 20,050 prompt tokens,
  and `truncated=0`; receipt/journal hashes are `5c9d6a27...800f4` and
  `2ed8eaca...b1e7`.
- Router, critic, and reranker probes return strict JSON at HTTP 200 with zero
  fallbacks. The embedding alias returns exactly 4,096 dimensions; its receipt
  hash is `fb1d9fc7...34a94`.
- Qwen generation returns strict JSON through its alias when thinking is
  disabled (`4f0a1ef0...69eca`). The attempted `medium` level fails HTTP 500
  because this installed abliterated build reports that it does not support
  thinking (`a4783b2c...12d1a`); the operator explicitly selected disabled
  thinking for the exact generation profile.
- The replacement mode-0600 config is
  `~/.agency-runtime/configs/ar297-litellm-a4e213d6b454ca90.yaml`, SHA-256
  `a4e213d6...97348`. Product schema/load plus authenticated deployment
  validation exit 0 at `fb8d3384...f680f`: all six deployment IDs and backend
  mappings match, direct Ollama is disabled, every inference profile uses
  LiteLLM, embedding is 4,096-dimensional, and only the credential environment
  name is persisted. `agency config validate` exits 2 only for the expected
  cold-host loading/trust warnings (`03c2747b...d617c`), so installed live
  validation remains open.
- Agency-level critic, text-reranker, child-judge, and two-input normalized
  embedding probes exit 0 at `f1ec2f09...e142`, `6c220204...c1dc`,
  `82a1abf3...c244`, and `0af8e0a4...92a6`. The first no-thinking synthetic
  planner call exits 1 solely on `plan_missing_codebase_discovery` at
  `cfe56a4f...71dcc`; the bounded planner repair and full canary remain the
  acceptance authority rather than relabeling that response as a pass.
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
  `task-agency-router`, then explicitly approved disabled Qwen generation
  thinking after the installed model rejected `medium`; no Jina route is
  permitted.
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
- [x] Stage aliases resolve to the approved local backends, preserve the 4,096
      embedding dimension, and prove a 20,050-token no-fallback child response
      at a 32,768-token context without truncation.
- [x] The new mode-0600 exact config contains only LiteLLM inference routes and
      passes strict structural, model, credential, and deployment validation.
- [ ] The exact config passes clean installed live validation in each target
      production container and on the Linux host.
- [ ] A fresh no-bypass Codex transaction proves one resolved Mistral child
      decision, v6 delivery/consumption, accepted finalization, and attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
