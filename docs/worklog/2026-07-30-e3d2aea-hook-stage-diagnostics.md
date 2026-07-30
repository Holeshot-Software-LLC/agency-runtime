---
title: "Worklog detail: Harden hook stage diagnostics"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [codex, hooks, evidence, review, windows]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/handoffs/issue-AR-203.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: e3d2aeab3f1473d775fabe03ac409ec633f39415
short: e3d2aea
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
---

# Worklog detail: Harden hook stage diagnostics

## Purpose

Close direct evidence gaps found during bounded review of the AR-203 product
activation repair and keep the broader component suite aligned with the current
model-receipt contract.

## Approach

The hook-marker parser now accepts Windows CRLF without relaxing its exact
allowlist. A real failing hook bridge proves that an accepted event emits
`failed` and never `completed`. The multi-unit delegation test now confirms
that a response claiming an unavailable model without a receipt must correct
`actual_model_selected` alongside its other stale fields.

## Challenges encountered

The first broad component run stopped on two parameterizations of the same
stale model-field assertion. An isolated rerun reproduced both failures. The
runtime behavior was retained and the obsolete test expectation was corrected.

## Decisions and alternatives

Production model evidence was not weakened to satisfy the old assertion.
Arbitrary stderr, unknown events, unknown stages, and unbounded counts remain
excluded from durable proof.

## Verification

- Decision conformance baseline passed and killed 19/19 mutations with zero
  survivors or invalid results.
- Both review passes completed; no unresolved Critical or High finding remains.
- The complete changed-component suite passes 200 tests under `-W error`.
- Ruff check and format checks pass for the review delta.
- Documentation validation passes for 550 Markdown files.

## Follow-ups

Run the named fast production spine, merge and exact-install the resulting
build for Codex and ZCode, then request authorization for one replacement
ordinary canary under
[AR-203](../roadmap/issue-AR-203-prove-product-canary-write-and-activation.md).
