---
title: "AR-01: Selection explain receipts"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [routing, observability]
related:
  - docs/decisions/0015-versioned-selection-explain-receipts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-01
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/1"
depends_on: []
blocks: []
---

# AR-01: Selection explain receipts

## Problem

Operators need to understand why a specialist was selected without reading selector internals or manually replaying a request. A route that cannot expose its candidates, rejections, and applied signals is difficult to debug or trust.

## Current state

This item is implemented. The runtime exposes a stable `agency.selection_explain.v1` receipt through the CLI, HTTP, and MCP surfaces. Receipts include selected and considered specialists, rejection reasons, policy and domain-expansion signals, cache and stickiness state, selection status, and work-unit evidence. Automated tests cover the public surfaces, and the corresponding tracker issue is closed as completed.

## Approach

Keep explanation generation as a read-only projection over routing evidence. Preserve the stable schema, keep normal routing behavior unchanged when no explanation is requested, and extend the receipt whenever a new selector layer introduces operator-relevant evidence.

## Dependencies

None.

## Acceptance

- [x] CLI users can request a machine-readable routing explanation.
- [x] HTTP and MCP users receive the same explanation contract.
- [x] The receipt identifies selected and considered specialists plus available rejection reasons.
- [x] Policy, domain expansion, cache, and stickiness effects are represented.
- [x] Existing routing behavior is unchanged when explanation output is not requested.
