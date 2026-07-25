---
title: "AR-118: Reconcile native-child activation evidence"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [delegation, activation, correlation, hooks, evidence]
related:
  - agency_runtime/core/store/delegation_activation.py
  - agency_runtime/core/store/evidence.py
  - agency_runtime/server/mcp_tools.py
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/decisions/0079-route-native-children-once-and-bound-unplanned-reroutes.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-118
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/131
depends_on: [AR-116]
blocks: [AR-119]
---

# AR-118: Reconcile native-child activation evidence

## Problem

A real Codex turn consumed the correct exact-version, one-use specialist
activation in the native child, but the parent recorded the native task label
as the worker identity. The consumed activation and delegation event therefore
remained unlinked. Finalization and the Stop hook repeatedly demanded an
activation that already existed, with no supported recovery operation.

## Current state

The store correctly refuses to rewrite an executed delegation from untrusted
caller input. However, it does not use the already-consumed activation receipt
as the authoritative worker lineage, and it cannot repair an unlinked event to
that exact cryptographically bound lineage.

## Approach

Resolve public delegation calls against an existing consumed activation before
recording worker identity. Permit a prior unlinked delegation event to be
corrected only when the incoming identity exactly matches the consumed grant's
worker kind, worker ID, and native run ID. Continue rejecting every correction
without that authoritative receipt. Exercise both consume-before-delegate and
incorrect-delegate-before-consume orderings.

## Dependencies

AR-116 defines parent-planned one-use activation and native child correlation.
ADR-0079 makes the consumed activation receipt authoritative for this narrow
reconciliation.

## Acceptance

- [x] agency.delegate derives worker lineage from a matching consumed activation.
- [x] An unlinked executed event can be corrected only to consumed-receipt lineage.
- [x] Conflicting lineage without a consumed receipt remains rejected.
- [x] Both event orderings have regression coverage.
- [x] Finalization accepts the reproduced turn without an activation retry.
- [ ] The exact installed artifact passes the flow in a genuinely new Codex task.
