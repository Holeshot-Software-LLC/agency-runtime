---
title: "Disambiguate provider fallback receipts from inference-stage ordinals"
status: open
category: roadmap
created: 2026-08-24
updated: 2026-08-24
tags: [inference, receipts, telemetry, fallback]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - agency_runtime/core/store/preflight.py
  - tests/test_store_preflight_coverage_final.py
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-284
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-284: Disambiguate provider fallback receipts from inference-stage ordinals

## Problem

Strict workforce inference records planner/recruiter/critic attempts in
`model_receipts.attempted_fallbacks` by enumerating the inference stages. A
three-stage, single-profile call therefore persists `0`, `1`, and `2` even when
the routing receipt says `fallback_considered=false`,
`fallback_applied=false`, and every attempt used the same provider profile.
Consumers can incorrectly read those stage ordinals as provider fallbacks.

## Current state

The live OpenClaw trace retained for AR-283 has three successful wrapper
receipts on `linux-task-agency-router` / `litellm` / `task-agency-router` and no
cross-provider fallback, but its `attempted_fallbacks` values are `0`, `1`, and
`2`. Current acceptance therefore derives provider fallback from the routing
receipt and provider identities, not that column. No actual answering model is
available because the LiteLLM callback produced no authoritative receipt.

Tracker creation is pending separate authorization. No tracker, PR, or hosted
workflow mutation was performed while recording this local issue.

## Approach

1. Define separate durable meanings for inference-stage ordinal and provider
   fallback count.
2. Add expected-red coverage for multi-stage inference through a single
   profile and for a real provider-chain fallback.
3. Preserve schema compatibility or add a bounded migration without rewriting
   historical receipts.
4. Update evidence projections and documentation so acceptance queries cannot
   confuse stage order with fallback behavior.

## Dependencies

- Store receipt schema and preflight transaction compatibility.
- Existing routing receipt fields remain the authoritative fallback evidence
  until this issue is resolved.
- Tracker creation requires separate authorization.

## Acceptance

- [ ] Stage ordinal and provider fallback count have distinct, documented fields.
- [ ] A three-stage call through one profile records provider fallback count zero.
- [ ] A genuine provider-chain fallback records the exact fallback count.
- [ ] Existing historical rows remain readable without reinterpretation.
- [ ] Focused Store, inference-profile, and receipt-projection tests pass.
- [ ] Tracker creation and linkage remain pending separate authorization.
