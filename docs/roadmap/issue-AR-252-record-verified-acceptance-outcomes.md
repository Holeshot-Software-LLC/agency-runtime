---
title: "AR-252: Record verified acceptance outcomes so automatic promotion can fire"
status: proposed
category: roadmap
created: 2026-08-05
updated: 2026-08-05
tags: [workforce, promotion, evidence, native-child, outcomes]
related:
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
  - agency_runtime/core/store/workforce.py
  - agency_runtime/core/store/native_child.py
  - agency_runtime/core/workforce/promotion.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-252
priority: p2
tracker_url: null
depends_on: []
blocks: []
---

# AR-252: Record verified acceptance outcomes so automatic promotion can fire

## Problem

The automatic contractor→employee promotion policy (AR-242) requires
`promotion_readiness` evidence that only receipt-validated **acceptance**
events can satisfy: `event_type="acceptance"`, a consumed activation receipt,
and cross-checked independent-verifier refs
(`independent_verifier_worker_id`, `independent_verification_receipt_id`,
validated against the verifier's consumed receipt in the same session and
trace — `_validated_outcome_evidence`,
`agency_runtime/core/store/workforce.py`).

The live outcome path now evaluates the promotion policy on every native
child terminal outcome (`record_native_assignment_outcome` runs
`_auto_promote_if_ready` in the same transaction). But that path records
`event_type="assignment"` events with no verifier evidence, so readiness can
never be met from live delegations alone. Automatic promotion therefore
remains dormant in production: the policy is wired and tested, but the
evidence pipeline that would trigger it does not exist.

## Proposal

When a turn's plan contains an independent assurance unit whose verifier
worker consumed its own activation receipt and its review unit accepted the
producing worker's artifact, record an `acceptance` performance event for the
producing worker carrying:

- the producer's consumed activation receipt id,
- `independent_verifier_worker_id` = the assurance unit's worker,
- `independent_verification_receipt_id` = the assurance unit's consumed
  receipt,

so `_validated_outcome_evidence` can validate it and
`promotion_readiness` counts it. The natural recording point is turn
finalization, where the Store already correlates both units' delegation and
receipt evidence.

## Acceptance

- A turn with a producer unit and a disjoint after-artifact assurance unit,
  both with consumed receipts and accepted outcomes, produces one
  receipt-validated acceptance event for the producer.
- Three such turns (distinct work units, outside the review window) trigger
  `_auto_promote_if_ready` on the live path with no operator action, and the
  promote event records `actor="promotion-policy"` with the readiness
  evidence document.
- Turns without an assurance unit, with a shared-identity verifier, or with
  unconsumed receipts record no acceptance event.
