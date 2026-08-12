---
title: "Historical session handoff — Rule 4 evidence"
status: draft
category: documentation
created: 2026-08-10
updated: 2026-08-12
tags: [historical, handoff, rule-4, child-delivery]
related:
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: docs/roadmap/handoffs/issue-AR-119.md
---

# Historical session handoff — Rule 4 evidence

This file preserves the bounded 2026-08-10 engineering snapshot that first
separated an Agency-written staffing row from native-host delivery evidence. It
is not a current recovery capsule or completion authority. Resume AR-119 from
the [active recovery capsule](roadmap/handoffs/issue-AR-119.md), interpret the
rules from the [founding vision](roadmap/AR-119-founding-vision.md), and read
current cell states from the
[rule and host evidence matrix](roadmap/AR-119-rule-host-evidence-matrix.md).

## Durable finding retained from the snapshot

The snapshot established the evidence boundary that remains in force: a card
counts for Rule 4 only when an artifact written by the native host shows the
exact delivered card hashes before the child first speaks. A
`specialist_load` or similarly named Store row proves only what Agency
attempted. It is diagnostic and cannot originate a green delivery verdict.

The snapshot also introduced read-only child-artifact inspection and host
wiring-drift checks for Claude and Codex. Those implementation facts remain
useful, but their source tests and historical artifacts do not establish a
current installed candidate or cross-host parity.

## Historical claims that no longer govern

The original handoff mixed layer labels, saying native artifact inspection was
done while the real harness run had not occurred, and reported only legacy
deliveries from the retired planned-delegation transport. Later prior-candidate
evidence added Claude host-authored multi-card child artifacts and Codex
negative observations. Neither binds the matrix's exact candidate, and ZCode,
Hermes, and OpenClaw remain unproven at the cutoff. The active matrix owns the
current layer states and limitations.

The old planned-child, parent-issued activation, work-unit, and one-use receipt
model is preserved in Git history for provenance. It must not be reconstructed
as the current delivery mechanism. Under the nine-rule vision, inference alone
chooses cards, the native harness alone chooses whether to spawn, and the
host-authored child artifact alone proves delivery.

## Current continuation

The active capsule owns the exact blocker order, verification commands,
checkpoint discipline, and next bounded package. Do not update this historical
pointer with live progress; update that single active capsule and the canonical
roadmap records instead.
