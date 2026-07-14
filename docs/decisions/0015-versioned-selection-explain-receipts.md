---
title: Publish versioned selection-explain receipts
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [routing, explainability, schema]
related:
  - docs/roadmap/issue-AR-01-selection-explain-receipts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0015
type: decision
deciders: []
---

# ADR-0015: Publish versioned selection-explain receipts

## Context

A selected specialist list does not show why candidates were accepted or rejected, whether policy or semantic matching contributed, or whether cache and session state changed the result. Operators need a stable artifact for debugging and automation.

## Decision

Expose a versioned selection-explain receipt through the command line, HTTP, and MCP surfaces. The receipt includes selected specialists, considered and rejected candidates with reasons, policy hits, domain expansion, cache and stickiness state, selection status, roster size, and work-unit evidence.

Give the receipt an explicit schema version. Additive evolution may preserve the version; incompatible shape or meaning changes require a new version.

## Consequences

- Routing behavior can be inspected without reproducing internal execution manually.
- Multiple interfaces share one explainability contract.
- Schema stability becomes a public compatibility commitment.
- Explain output must avoid leaking secrets or unrelated prompt content.

## Alternatives

- Return only selected identifiers. Rejected because it cannot explain policy or rejection behavior.
- Rely on debug logs. Rejected because logs are not a stable interface and may not be available to callers.
- Expose internal objects without a version. Rejected because consumers could not distinguish compatible evolution from breakage.

## Provenance

Commit 42f6580 introduced the agency.selection_explain.v1 receipt and exposed it through CLI, HTTP, and MCP with regression coverage.
