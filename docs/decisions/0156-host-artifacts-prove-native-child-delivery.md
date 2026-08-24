---
title: "Use host-authored artifacts as native-child delivery proof"
status: accepted
category: decisions
created: 2026-08-12
updated: 2026-08-12
tags: [evidence, native-child, hosts, routing, correlation]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - agency_runtime/core/child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0156
type: decision
deciders: [lkrammes]
---

# ADR-0156: Use host-authored artifacts as native-child delivery proof

## Context

ADR-0027 made SQLite the authority for externally visible runtime claims so
model prose and partial lifecycle events could not invent success. Native-child
card delivery crosses a sharper trust boundary: the same Agency code under test
can write a `specialist_load` Store row whether or not the native host placed
that card in the child context. Treating that row as delivery proof makes the
producer attest to its own success.

Claude and Codex write durable transcripts that show the child's received
context. Prior-candidate Claude artifacts show delivery, while prior-candidate
Codex artifacts show real child creation with no delivered card. Those
observations established the evidence boundary but do not establish the
matrix's exact-candidate installed/live state. ZCode, Hermes, and OpenClaw
remain unproven and must expose equivalent host-authored artifacts before their
Rule-4 claims can turn green.

## Decision

For the claim "this native child received these specialist cards before it
spoke," the origin authority is an artifact written by the native host. A green
proof must bind the parent and child identities, host and install identity,
inference decision, immutable card versions and hashes, delivery position before
first child speech, and artifact digest.

SQLite remains the canonical bounded query and audit projection after a
validator reads the host artifact and persists its verified identity and digest.
An Agency-authored route, load, activation, lifecycle, header, or canary row may
support correlation and diagnosis, but cannot originate or upgrade the delivery
claim. Missing or unavailable host evidence is `unproven`, never inferred from
Agency state.

This narrows ADR-0027 for one cross-boundary observation; its authority rules for
all other correlated runtime claims remain in force.

## Consequences

- Rule-4 canaries cannot pass from Store rows or response prose alone.
- Each host adapter needs a bounded parser for its own artifact shape and an
  explicit unsupported/unavailable state.
- Artifact digests and normalized proof can be queried from SQLite without
  storing unrestricted child content.
- Contract simulations, hook execution, and Agency load rows remain useful but
  are visibly weaker than live host delivery proof.

## Alternatives

- **Trust `specialist_load`.** Rejected because Agency would certify its own
  attempted delivery.
- **Trust a child response header.** Rejected because model prose is forgeable
  and can be copied without card delivery.
- **Query host artifacts directly for every UI view.** Rejected because parsing
  and correlation must be bounded once, with a durable auditable projection.

## Provenance

Commit `929c0599` implemented bounded host-artifact card-delivery evidence. This
decision governs its authority boundary; the worklog retains the exact subject
and history.
