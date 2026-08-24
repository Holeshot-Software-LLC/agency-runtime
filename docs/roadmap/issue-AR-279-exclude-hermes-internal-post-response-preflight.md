---
title: "Exclude Hermes internal post-response calls from Agency preflight"
status: open
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [hermes, lifecycle, inference, evidence, reliability]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - agency_runtime/core/installer_payload_hermes.py
  - agency_runtime/adapters/hermes/
  - tests/test_hermes_turn_trace_payload.py
  - tests/test_adapter_parity.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-279
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-279: Exclude Hermes internal post-response calls from Agency preflight

## Problem

After Hermes has accepted and delivered a user turn, a separate native internal
post-response call traverses the installed Agency preflight hook as though it
were a new nontrivial user request. The strict planner then consumes the Hermes
harness-scoped LiteLLM profile and can persist an unrelated
`preflight_failed` run. These rows do not block the already completed user
reply, but they add avoidable provider work and misleading failure evidence.

## Current state

Fresh live Telegram proof on 2026-08-24 completed and delivered three intended
Hermes user turns with correct `host=hermes` attribution, Store-backed headers,
and exact parent routing. Immediately around the status and two substantive
response-delivery boundaries, separate runs `a9874148...`, `e38ecc07...`, and
`3608e1d2...` began under the same native session but with distinct internal
turn identities. Failure receipts `2934adb1...`, `60547574...`, and
`3f54ebbc...` each record two strict planner contract rejections on profile
`linux-task-agency-router`, provider type `litellm`, and exact alias/model-group
`task-agency-router`.

The intended user runs remained terminal `completed`, their transformed replies
were written by Hermes and delivered through Telegram, and native and Agency
configuration hashes stayed unchanged. The router alias is not an actual-model
claim. No internal prompt content, credential, or transport identifier is
retained in this issue.

## Approach

1. Reproduce the internal post-response lifecycle call in a focused Hermes
   bridge test while retaining its native lifecycle metadata.
2. Distinguish user-authored parent turns from session-title, summary, delivery,
   or other internal host invocations before Agency opens a preflight run.
3. Skip only a positively identified internal invocation; unknown or malformed
   lifecycle evidence must remain fail closed.
4. Prove that ordinary Hermes status, skill, and substantive user turns still
   receive Agency headers, routing, finalization, and Store correlation.
5. Reinstall only the Hermes Agency bridge from the changed checkout and use a
   fresh native session plus a genuinely new work unit for live verification.

## Dependencies

- Hermes must expose a stable, testable discriminator for internal versus
  user-authored invocations, or the bridge must derive one from authenticated
  native lifecycle evidence.
- Existing AR-119 finalization, child-delivery, and fail-closed policies remain
  authoritative.
- Tracker creation requires separate authorization and is intentionally
  pending; no outward-facing write was made in this package.

## Acceptance

- [ ] A focused regression fails before and passes after the bounded lifecycle
      classification repair.
- [ ] Internal post-response calls create no Agency run, routing decision, or
      provider receipt.
- [ ] User-authored Hermes status, skill, and substantive turns retain correct
      `host=hermes` attribution and Store-backed five-line headers.
- [ ] Unknown, missing, replayed, and cross-session lifecycle identities remain
      blocked without weakening finalization or delivery checks.
- [ ] Native Hermes configuration, model routes, plugin inventory, and other
      harnesses remain unchanged.
- [ ] Focused Hermes/adapter/security tests and proportionate local gates pass.
