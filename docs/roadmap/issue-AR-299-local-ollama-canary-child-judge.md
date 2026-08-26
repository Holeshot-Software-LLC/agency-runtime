---
title: "AR-299: Allow a local Ollama canary child judge"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [canary, inference, ollama, providers, security, evidence]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - agency_runtime/core/canary_judge_provider.py
  - tests/test_canary_child_judge_provider.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-299
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-299: Allow a local Ollama canary child judge

## Problem

AR-297's approved Linux production topology requires the canary child judge to
use a free local model. The existing fail-closed pin accepts Codex or Claude
CLI providers and Anthropic-compatible inference profiles, but rejects an
otherwise valid keyless Ollama profile before inference. Falling back to a
subscription would violate the approved topology, while treating the legacy
global judge as a canary pin would lose the exact requested/answered identity.

## Current state

- Per-harness child-judge pins resolve exactly one provider or inference
  profile, remove fallbacks, and retain separate requested and answered
  identities.
- The structured-provider seam already supports bounded Ollama JSON calls,
  literal-loopback safety, exact actual-model receipts, and `think: false`.
- `mistral-small3.2:24b` is installed locally at Ollama digest `5a408ab55df5`;
  local metadata records 24.0B parameters, Q4_K_M, 131,072-token context, and
  Apache-2.0 licensing.
- Tracker creation is prohibited in the active AR-297 task. This local record
  therefore has no tracker URL, and tracker parity remains an explicit gate.

## Approach

Admit `ollama` beside `anthropic` in the canary-only supported-profile
allowlist. Continue materializing only an already-declared named profile,
requiring exact single-name resolution, a safe endpoint, an available model,
and an exact config/environment pin match. Keep ordinary provider order and
ordinary workforce routing unchanged.

Use the existing structured Ollama transport without adding model-specific
behavior. The approved child profile carries no thinking level, so the
transport explicitly sends `think: false` and requires schema-valid final JSON.
Reject credentialless non-loopback HTTP endpoints before inference.

## Dependencies

- ADR-0160 owns per-harness canary child-judge pinning and no-fallback behavior.
- ADR-0174 owns the local keyless profile extension.
- AR-297 owns the clean-container and later ordinary-process live proof.
- Tracker creation requires separate outward-write authorization and is not
  authorized by this implementation.

## Acceptance

- [x] One named keyless loopback Ollama profile resolves as the sole canary
      child judge without entering or reordering the ordinary provider chain.
- [x] Ambiguous names, unsupported adapters, unsafe remote HTTP, unavailable
      profiles, and config/environment mismatches remain fail-closed.
- [x] Focused tests pass with warnings treated as errors.
- [ ] A clean AR-297 container canary records the requested local profile and
      the actual local model that answered.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.

## Verification evidence

The rebuilt exact Codex canary resolves the explicit configuration and proceeds
past the missing-pin failure that created this issue, but both bounded attempts
exit at staffing critique before a child is selected. No requested/actual child
judge receipt exists, so the clean live acceptance item remains open. Direct
bounded route probing separately proves `mistral-small3.2:24b` answers the
required schema with thinking disabled; that transport receipt is not
substituted for a completed canary child receipt.

The final approved ordinary Hermes retry also used local Mistral with native
reasoning disabled, but Agency preflight failed during recruitment before any
child selection. Trace
`20260826_143220_d88838:59ceb645-aba9-4910-9cb6-1f25d61efd89:2f835640`
contains no Agency model receipt or canary attestation. It therefore adds no
requested/actual child-judge proof and leaves both live acceptance and tracker
parity open.
