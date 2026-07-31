---
title: "Worklog detail: Bind the indivisible review canary plan"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [activation, codex, inference, planning, review, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 271e5a0
short: 271e5a0
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Bind the indivisible review canary plan

## Purpose

Repair exact Codex activation after real inference selected a valid reviewer but
produced a plan shape that the closed-world canary correctly rejected.

## Approach

Carry the canary's explicit one-unit and `review-report` requirements into the
inference prompt, structured schema, semantic parser, and cache identity. The
pipeline applies those constraints only to the exact native-verified canary;
ordinary requests retain open-ended team planning. Inference continues to
choose the worker, while deterministic code only rejects a plan that violates
the user's fixed indivisible review contract.

## Challenges encountered

The installed build first produced two accepted units, causing
`activation_canary_contract_invalid:binding_count`. Constraining the count then
exposed `activation_canary_contract_invalid:artifact_kind` because inference
classified the single code-review result as generic analysis. Both provider
stages had applied valid structured responses, so neither failure was a trust
or provider-availability problem.

## Decisions and alternatives

A blind full-route retry was rejected because it could conceal a stable
contract mismatch. The repair does not synthesize a unit, rewrite a selected
worker, or add deterministic selection. Two curated mutations prove that
removing either request-bound constraint is detected.

## Verification

- The activation, workforce-inference, and decision-conformance boundary passes
  72 warning-strict tests.
- Ruff check and formatting pass all six changed Python files; diff integrity
  is clean.
- A fresh real-provider replay against a private clone of the installed Store
  accepted inference-selected `code-reviewer`, one `review-report` unit, one
  binding, one assignment, and immediate delegation with no error.

## Follow-ups

Run the named local fast gate, merge and exact-install the repair, then prove
native activation before consuming the build's one product-trial allowance.
