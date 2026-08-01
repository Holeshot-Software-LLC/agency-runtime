---
title: "AR-224: Simplify Agency evidence header"
status: open
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [enhancement, product, header, evidence, usability]
related:
  - README.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/header/contract.py
  - agency_runtime/core/header/finalize.py
  - tests/test_codex_activation_canary.py
  - tests/test_header_contract_hardening.py
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-224
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-224: Simplify Agency evidence header

## Problem

The visible Agency header requires `Why` and `How it shaped outcome` even when
those fields merely restate selection and delegation evidence. Their generic
text adds noise, lengthens every substantive response, and creates two more
schema fields that can trigger a correction loop without helping the user
verify what actually ran.

## Current state

The Stop verifier, header parser, activation canary, dashboard projections, and
tests currently require both fields as part of the exact six-line contract.
They cannot be removed only from rendering: doing so would make every otherwise
valid first response fail header validation and request a repair.

## Approach

1. Reduce the canonical visible header to factual execution fields: loaded,
   delegated, skills, selected model, and recruitment source.
2. Update generation, parsing, Stop verification, canary evidence, dashboard
   rendering, documentation, and tests as one atomic contract change.
3. Preserve evidence fidelity and zero-correction acceptance; do not replace
   the removed prose with another generic summary field.

## Dependencies

AR-223 must first prove that the current header is emitted from accepted live
execution evidence. Simplification must not obscure its execution failure.

## Acceptance

- [ ] `Why` and `How it shaped outcome` are absent from the canonical header.
- [ ] Every producer and consumer accepts the same reduced schema on the first
  response without a repair loop.
- [ ] The remaining fields still match Store and host evidence exactly.
- [ ] Focused hook, canary, dashboard, documentation, lint, and format checks
  pass.
