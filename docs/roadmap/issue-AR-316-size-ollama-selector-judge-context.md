---
title: "AR-316: Size Ollama selector-judge context for complete catalogs"
status: open
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [ollama, inference, selector, native-child, context]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - agency_runtime/core/selector/judge_protocol.py
  - tests/test_selector_judge_refactor.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-316
priority: p0
tracker_url: null
depends_on: [AR-299]
blocks: []
---

# AR-316: Size Ollama selector-judge context for complete catalogs

## Problem

The Ollama selector-judge transport hardcodes `num_ctx=8192` even when the
caller supplies a complete candidate universe. Exact AR-297 Codex attempt C2
sent the approved free Mistral judge a 19,520-token prompt covering all 59
eligible specialists. Ollama honored the request-level 8,192-token cap,
truncated the prompt to 8,191 tokens, and returned an unusable one-token
response. Agency correctly persisted `native_child_inference_unavailable` and
withheld the specialist card, but the clean production canary cannot complete.

## Current state

- System Ollama 0.30.0 is active at the approved loopback endpoint. The exact
  `mistral-small3.2:24b` model is present at digest prefix `5a408ab55df5` and
  declares a 131,072-token model context in AR-299.
- Service logs correlate the C2 request at 2026-08-26 19:07:07-04:00: prompt
  19,520, limit 8,192, new length 8,191. The HTTP request returns 200 after
  26.282 seconds, but the selector receives no valid decision.
- `build_judge_payload` itself sends `num_ctx=8192`; changing the Ollama service
  default or model metadata cannot override that request value.
- A bounded 32,768-token request for the same model and endpoint is the proposed
  direct-transport repair. The operator instead selected AR-317's LiteLLM-only
  host topology, so this direct Ollama defect remains open but no longer blocks
  the AR-297 exact candidate.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Retain the exact diagnosis for a future bounded direct-Ollama transport repair.
AR-297 does not change the hardcoded request or exercise that route. AR-317
instead projects a dedicated no-fallback LiteLLM alias whose backend owns the
32,768-token context, then proves the complete no-bypass Codex transaction with
the supported 600-second outer activation timeout.

## Dependencies

- AR-299 and ADR-0174 own the exact free local child-judge route.
- AR-315 proves the immutable managed-install identity now reaches this stage.
- AR-297 owns fresh-container, Store, host-artifact, and attestation evidence.
- AR-317 and ADR-0181 own the operator-selected LiteLLM alias topology.

## Acceptance

- [x] Exact Store, rollout, and Ollama logs correlate the failure to request-
      level 8,192-token truncation, not model absence or endpoint failure.
- [x] The operator declines the direct route for AR-297 and selects a
      Mistral-backed LiteLLM alias instead.
- [ ] The bounded transport and large-catalog regressions pass warning-strict.
- [ ] A fresh exact Codex production-container transaction records the actual
      child-judge model, one v6 delivery and consumption, accepted finalization,
      and current attestation without a bypass.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
