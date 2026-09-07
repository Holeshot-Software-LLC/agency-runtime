---
title: "Retire the superseded mandatory manual-CI checklist"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [ci, backlog, governance, cost]
related:
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/acceptance/evidence/AR-177-manual-ci-reconciliation-20260907.md
  - .github/workflows/ci.yml
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0234
type: decision
deciders: [maintainers]
---

# ADR-0234: Retire the superseded mandatory manual-CI checklist

## Context

AR-177 implements manual-only exhaustive CI at 60543e1. Its only unchecked July
criteria demand a hosted manual run after billing repair and an exact final
release gate. ADR-0105/AR-186 supersede the mandatory-release portion of
ADR-0101 and explicitly make exhaustive diagnostics optional. Keeping the
older checklist open as mandatory contradicts that accepted operating rule.

Current workflow and 222 focused contracts preserve explicit dispatch gates,
four coverage shards, 97 percent, six compatibility sessions and fail-closed
aggregation. Read-only history finds one August 17 manual run; whitespace
validation failed before coverage/compatibility allocation. That run is not
green evidence, and no billing causality is established.

## Decision

Retire AR-177 as wont_do/superseded by AR-186, not as accepted against its
historical seven criteria. Preserve the original checked and unchecked states
and failed hosted readback. Retire the duplicate mandatory completion checklist,
not the implemented manual-only CI behavior.

Keep .github/workflows/ci.yml, its tests, explicit manual dispatch requirement,
four shards, unchanged 97-percent floor and six compatibility sessions intact.
An explicitly requested future manual run must still pass every applicable
gate; optional does not mean a failed diagnostic is green.

This applies ADR-0105 and does not supersede it, amend current release policy,
authorize a dispatch or imply billing/settings authority. AR-156/159 retain
their own platform and hosted-enforcement requirements; AR-176's unresolved
inventory criteria remain open.

## Consequences

The queue loses one obsolete legacy checklist without inventing a successful
manual run, Windows evidence, billing repair or cost savings. The owner can
still request exhaustive integration whenever it is useful. Every original
result and requirement remains discoverable through the successor links.

## Alternatives

- Mark all seven old criteria satisfied: rejected; the manual topology and
  final release proof do not exist.
- Dispatch now solely to close the issue: rejected; it conflicts with the
  accepted explicit opt-in policy and consumes unrequested exhaustive budget.
- Keep an obsolete mandatory blocker forever: rejected; AR-186 already owns
  the current delivery rule.
- Remove manual verification or relax 97 percent: rejected; neither is needed
  to reconcile the planning record.

## Verification basis

At d2125438, the focused workflow/session/classifier package passes 222 cases
with five Windows-named deselections (6.70s). No production bytes change.
The dated failed manual run and all job outcomes are preserved in the receipt.
