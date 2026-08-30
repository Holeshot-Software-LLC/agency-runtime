---
title: "AR-81: Prevent incompatible specialists from sharing a direct context"
status: done
category: roadmap
created: 2026-07-17
updated: 2026-07-19
tags: [routing, prompts, isolation, delegation, security]
related:
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0062-isolate-directives-and-route-units-first.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-81
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/81"
depends_on: [AR-25, AR-26, AR-58]
blocks: []
---

# AR-81: Prevent incompatible specialists from sharing a direct context

## Problem

Direct-delivery hosts could concatenate multiple full directive prompts into one
context. An implementer and independent reviewer could then issue competing
instructions without an isolation or authority boundary.

## Current state

Direct hosts hydrate one directive specialist by default. The explicitly
governed `agents-orchestrator` plus `chief-of-staff` no-match pair is delivered
as one compact resident-manager kernel, not as two competing ordinary prompts.
Isolated hosts retain separate native specialist activation. Final integrated
verification remains in progress.

## Approach

Treat a worker context as a single-directive authority boundary. Preserve other
selected identities as routing and delegation suggestions without concatenating
their raw prompts. Keep the resident managers in one bounded management kernel,
and run reviewers and other independent roles in separate DAG nodes on hosts
that can isolate children. PR #114 passed the complete Windows/Linux host and
artifact matrix, and the exact merged installation passed routing, delegation,
and installed Codex isolation canaries.

## Dependencies

AR-25 defines turn-scoped activation, AR-26 governs the fallback pair, and
AR-58 defines unit-aware specialist assignment.

## Acceptance

- [x] Unrelated specialist prompts never share a direct host context.
- [x] The governed no-match coordinator pair remains available together.
- [x] Isolated hosts can prepare separate specialist activations.
- [x] Regression tests exercise both allowed and rejected composition.
- [x] Full cross-host and merged-install gates pass.
