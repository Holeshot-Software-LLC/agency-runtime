---
title: "AR-64: Reject unproven LiteLLM router-alias echoes"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [litellm, models, receipts, observability, security, testing]
related:
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/roadmap/issue-AR-29-reconcile-litellm-model-and-router-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-64
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/65"
depends_on: [AR-29]
blocks: []
---

# AR-64: Reject unproven LiteLLM router-alias echoes

## Problem

A successful LiteLLM response can echo the requested router alias in its
`model` field without reporting the deployment that actually ran. When no
distinct routed candidate was present, reconciliation still promoted that echo
to `resolved_model`, fabricating actual-model evidence from a request identity.

## Current state

Exact qualified and unqualified response echoes of the requested model or
router group now remain router evidence only. Reconciliation uses a distinct,
allowlisted routed deployment when present and otherwise records the actual
model as unavailable. A provider is retained only when separate authoritative
provider telemetry exists.

## Approach

Make alias-echo handling an explicit fail-closed branch before ordinary
provider-response precedence. Cover unqualified and provider-qualified echoes
without deployment telemetry, while retaining the existing contract that a
distinct routed deployment wins over the echo.

## Dependencies

AR-29 and ADR-0047 define the separated requested, router, provider, and actual
model fields. This correction closes a trust-order gap in that implementation
without changing the receipt schema.

## Acceptance

- [x] An unqualified exact router-alias echo cannot become `resolved_model`.
- [x] A provider-qualified exact router-alias echo cannot become `resolved_model`.
- [x] Distinct routed deployment telemetry still reconciles normally.
- [x] Missing actual-model proof renders as unavailable in receipts and headers.
- [x] Focused, full-suite, exact-coverage, and installed callback smoke gates pass.
