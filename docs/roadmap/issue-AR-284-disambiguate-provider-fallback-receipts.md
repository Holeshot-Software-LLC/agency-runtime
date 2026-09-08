---
title: "Disambiguate provider fallback receipts from inference-stage ordinals"
status: in_progress
category: roadmap
created: 2026-08-24
updated: 2026-09-08
tags: [inference, receipts, telemetry, fallback]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - agency_runtime/core/store/preflight.py
  - tests/test_store_preflight_coverage_final.py
  - tests/test_provider_attempt_accounting.py
  - docs/decisions/0238-separate-provider-fallback-accounting-from-stage-order.md
  - docs/roadmap/acceptance/evidence/AR-284-attempt-accounting-20260908.md
  - docs/roadmap/handoffs/issue-AR-284.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-284
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/754
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

The 2026-09-08 bounded source repair is implemented and focused-tested. Actual
workforce and hiring chain boundaries now stamp separate configured entry,
dispatch fact and known prior-entry fallback count. The three wrapper writers
consume that count, not flattened order. Existing JSON carries versioned
stage/ordinal metadata; explicit wrapper unknowns persist as SQL NULL. No
schema migration or historical-row rewrite is performed. Semantic repairs do
not increment a fallback count; pre-request refusals do not count as calls;
unclassified legacy transport failures preserve uncertainty.

After the owner ended the code-first test deferral for wrap-up, the focused
three-file command passed all 161 cases in 2.58 seconds. Two bounded source
passes found no scoped correctness issue. No provider/model/native call,
owner Store mutation, installation, acceptance verdict or completion claim is
part of this package. See the [source checkpoint](acceptance/evidence/AR-284-attempt-accounting-20260908.md)
and governing ADR-0238. Uninstrumented producers deliberately remain unknown;
this does not assert complete dispatch telemetry for every transport.

Owner authorized the existing item's tracker mapping on 2026-09-08:
[#754](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/754).
The historical pending-authorization statements and original sixth acceptance
item below are preserved as provenance, not a current prohibition or a fresh
acceptance verdict. All original criteria remain unchecked.

### Historical diagnosis, 2026-08-24

The live OpenClaw trace retained for AR-283 has three successful wrapper
receipts on `linux-task-agency-router` / `litellm` / `task-agency-router` and no
cross-provider fallback, but its `attempted_fallbacks` values are `0`, `1`, and
`2`. Current acceptance therefore derives provider fallback from the routing
receipt and provider identities, not that column. No actual answering model is
available because the LiteLLM callback produced no authoritative receipt.

Tracker creation is pending separate authorization. No tracker, PR, or hosted
workflow mutation was performed while recording this local issue.

## Approach

The current bounded implementation follows ADR-0238: reuse existing JSON,
preserve unknown with the already-nullable SQL column, and stamp only at the
producer boundary. There is no new fallback policy or provider-chain rewrite.
The original implementation plan is retained below:

1. Define separate durable meanings for inference-stage ordinal and provider
   fallback count.
2. Add expected-red coverage for multi-stage inference through a single
   profile and for a real provider-chain fallback.
3. Preserve schema compatibility or add a bounded migration without rewriting
   historical receipts.
4. Update evidence projections and documentation so acceptance queries cannot
   confuse stage order with fallback behavior.

## Dependencies

- ADR-0238's explicit dispatch/chain semantics and generic-wrapper-only NULL
  handling. Installed evaluation and isolated acceptance remain outstanding.
- Store receipt schema and preflight transaction compatibility.
- Existing routing receipt fields remain the authoritative fallback evidence
  until this issue is resolved.
- Historical tracker authorization was granted on 2026-09-08; #754 is mapped.

## Acceptance

- [ ] Stage ordinal and provider fallback count have distinct, documented fields.
- [ ] A three-stage call through one profile records provider fallback count zero.
- [ ] A genuine provider-chain fallback records the exact fallback count.
- [ ] Existing historical rows remain readable without reinterpretation.
- [ ] Focused Store, inference-profile, and receipt-projection tests pass.
- [ ] Tracker creation and linkage remain pending separate authorization.
