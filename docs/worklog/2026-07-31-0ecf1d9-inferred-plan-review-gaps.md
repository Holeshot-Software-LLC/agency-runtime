---
title: "Worklog detail: Close inferred plan review gaps"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [workforce, inference, routing, safety, review]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0ecf1d9
short: 0ecf1d9
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/192
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Close inferred plan review gaps

## Purpose

Resolve all three valid findings from PR 192's first Codex review before the
README-story candidate is merged or installed.

## Approach

Pass the configured work-unit limit into compact-plan semantic parsing so an
oversized inferred response enters the existing bounded planner repair before
recruitment. Match release evidence against every specific install, deployment,
or release operation in the request and require positive verification language
from the evidence outcome. Remove generic `communication` from documentation
only when the request itself does not name a communication deliverable.

## Challenges encountered

The transport schema must retain the global 16-unit ceiling while a smaller
runtime configuration remains enforceable. The repair therefore belongs in the
semantic parser, which can feed the existing inference-owned correction turn,
rather than in deterministic plan construction. Generic generated claims could
also make any evidence row look positive, so release matching intentionally
uses the inference-authored outcome.

## Decisions and alternatives

The changes remain deterministic vetoes and request-grounded normalization.
They neither create a plan unit nor rank, select, hire, or declare a worker gap.
A dynamic transport schema was unnecessary because semantic rejection already
has one bounded inference repair path and produces exact validation feedback.

## Verification

- The exact four-case regression selection failed before the source repair.
- Seven focused regression cases pass after repair.
- Both complete changed modules pass 79 tests with warnings as errors.
- Routing correctness, workforce selection and hiring, and decision-conformance
  tests pass 115 cases with one intentional skip.
- Ruff check and formatting pass all five changed Python inputs.
- Documentation metadata and validation pass 572 Markdown files; diff integrity
  is clean.

## Follow-ups

Push the repair, complete the second Codex review pass, merge and exact-install
the resulting revision, then consume one fresh product trial. The local evidence
page and OpenClaw handoff remain contingent on that trial.
