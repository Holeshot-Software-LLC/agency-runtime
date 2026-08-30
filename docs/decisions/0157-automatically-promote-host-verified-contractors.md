---
title: "Automatically promote contractors from host-evidenced, independently verified outcomes"
status: accepted
category: decisions
created: 2026-08-12
updated: 2026-08-12
tags: [workforce, contractors, promotion, evidence, automation]
related:
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - agency_runtime/core/workforce/promotion.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0157
type: decision
deciders: [lkrammes]
---

# ADR-0157: Automatically promote contractors from host-evidenced, independently verified outcomes

## Context

The runtime already implements a default threshold of three successes and a
seven-day per-contractor review window, but live native work records assignments
rather than independently accepted outcomes. The policy is therefore dormant.
AR-119 cannot claim an autonomous contractor lifecycle while production evidence
cannot trigger promotion.

Promotion changes durable workforce status. Neither an Agency-authored
assignment row nor a producer judging its own work is sufficient authority.

## Decision

Automatic promotion is part of the default contractor lifecycle and the AR-119
critical path. After a contractor is at least seven days old, three distinct
accepted outcomes make it eligible for atomic promotion to employee without an
operator action.

Each counted outcome must bind:

- host-authored producer and verifier child evidence under ADR-0156;
- the exact delivered card hashes and produced artifact digest;
- a distinct governed verifier selected by inference under ADR-0118; and
- that verifier's accepted verdict for the exact artifact.

The three outcomes must be distinct, replay-safe, and attributable to the same
immutable contractor identity. Promotion records the full evidence manifest and
`actor="promotion-policy"` in the same transaction. Rejection, ambiguity,
shared producer/verifier identity, missing host evidence, or review-window age
does not count.

An operator may explicitly configure a stricter or disabled local policy, but
AR-119's default-path live proof must run with the governed three-success,
seven-day policy and demonstrate that no operator action is required.

## Consequences

- AR-252 is a P0 blocker rather than optional post-release automation.
- Existing work-unit and consumed-receipt validation must migrate to host child,
  card, artifact, verifier-decision, and verdict identities.
- CLI and dashboard readiness views must distinguish review-window, evidence,
  threshold, disabled-policy, and promoted states.
- Duplicate finalization or replay cannot produce multiple successes or
  promotions.

## Alternatives

- **Keep promotion operator-only.** Rejected because it leaves the autonomous
  lifecycle incomplete and makes 24/7 progression depend on manual action.
- **Count successful child exits.** Rejected because completion is not semantic
  acceptance and the producer cannot verify itself.
- **Promote immediately after one acceptance.** Rejected because one observation
  is too weak to establish repeatable contractor performance.

## Provenance

Commit `f85074fe` implemented the three-success and seven-day promotion policy.
This decision makes the live, independently verified trigger path part of the
AR-119 completion contract.
