---
title: "AR-216: Preserve required files in every product scenario scope"
status: done
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, evaluation, delegation, scope]
related:
  - README.md
  - agency_runtime/core/evals/product_scenarios.py
  - agency_runtime/core/unit_assignment.py
  - tests/test_product_scenarios.py
  - tests/test_unit_assignment_selector.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-216
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/216
depends_on: []
blocks: [AR-203, AR-204]
---

# AR-216: Preserve required files in every product scenario scope

## Problem

Codex review of PR 213 found that the product-plan resource extractor admits
API routes and prose tokens as filesystem resources. In the
`python-api-typescript-dashboard` scenario, `/health`, `GET/POST`,
`/api/tasks`, `list/create`, and `/api/tasks/{id}/complete` can consume the
eight-resource ceiling before required `web/app.ts` and `README.md` are
reached. A delegated worker then receives an incomplete implementation scope.

The finding was published after PR 213 merged and is unresolved on `main`.
It is independent of the `python-cli-service` hiring-critic failure now owned
by AR-217 and must not expand that P0 package.

## Current state

The authoritative review is
[`discussion_r3694585629`](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/213#discussion_r3694585629).
No all-six-scenario scope claim is valid until this item is implemented and
verified.

## Approach

1. Preserve explicit Required files before considering inferred resource
   tokens.
2. Reject HTTP routes, verbs, and prose actions as filesystem resources without
   weakening traversal and absolute-path safeguards.
3. Test the exact extracted resource scope for all six packaged product
   scenarios.

## Dependencies

ADR-0124 governs grading and execution against the inferred unit graph. This
bug corrects that graph's resource scope and does not change selection
authority.

## Acceptance

- [ ] Explicit Required files survive the bounded resource ceiling.
- [ ] API routes, HTTP verbs, and prose actions are not admitted as paths.
- [ ] All six product scenarios have exact scope fixtures.
- [ ] Existing traversal, absolute-path, and `python-cli-service` behavior stay
  green.
