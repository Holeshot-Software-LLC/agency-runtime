---
title: "Preserve OpenClaw model receipt fields"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [openclaw, model-receipt, finalization, compatibility]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-269-accept-null-openclaw-control-errors.md
  - agency_runtime/core/installer_payload_openclaw.py
  - tests/test_security_turn_boundaries.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-272
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119]
---

# AR-272: Preserve OpenClaw model receipt fields

## Problem

OpenClaw `2026.7.1-2` emits the authoritative requested provider and model on
the `model_call_ended` event, while its hook context may omit `modelId`. The
generated Agency plugin read only the context and its bounded bridge serializer
also discarded `requestedModel`, `modelGroup`, provider, resolved-model, call,
source, and status fields. Agency therefore persisted a content-free but blank
host model receipt and rejected finalization for missing
`actual_model_selected`.

## Current state

Fresh session `57f19f38-338d-4d93-9c46-eac7b6a4831a`, trace
`4959bd8c-a0bc-4e3d-bcb9-8cbcc1441547`, returned a visible Agency-shaped header
but the Store ended the run as `response_invalid`. Finalization event
`01af794d-fb97-41c5-8920-2a8bfc2a3558` records exact missing field
`actual_model_selected`; two model receipts record `requested_model` empty and
`resolved_model` unavailable. This is preserved as a failed attempt and grants
no activation or delivery claim.

The executable regression failed before the repair with Node exit 83 because
`event.model` was `task-general` while the serialized `requestedModel` was
empty. It passes after the bounded repair. A separate existing Store test in
the same command stopped in fixture setup on an untrusted temporary config
parent and did not exercise product behavior.

## Approach

Use `event.model` only when the supported OpenClaw context omits `modelId`.
Carry the documented model-receipt fields through the existing length-bounded
serializer. Keep LiteLLM router-backed resolved provider and actual model empty
unless authoritative telemetry supplies them; never promote the requested
alias into an actual-model claim.

## Dependencies

- OpenClaw `2026.7.1-2` installed hook contract for `model_call_ended`.
- Existing Agency model receipt and first-pass finalization contracts.

## Acceptance

- [x] An executable generated-plugin regression reproduces the exact empty-context event shape and fails before the repair.
- [x] The regression passes with requested model and model group equal to `task-general`, while router-backed resolved fields remain empty.
- [ ] A freshly reinstalled OpenClaw turn persists the requested host model, completes first-pass finalization, and delivers a Store-backed header.
- [ ] Focused OpenClaw transport, finalization, and Store tests plus repository documentation and diff gates pass.
- [ ] Tracker creation remains pending separate authorization.
