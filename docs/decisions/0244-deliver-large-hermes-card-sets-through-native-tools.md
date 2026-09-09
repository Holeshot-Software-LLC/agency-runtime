---
title: "Deliver large Hermes card sets through native tools"
status: accepted
category: decisions
created: 2026-09-09
updated: 2026-09-09
tags: [hermes, context, delivery]
related:
  - docs/worklog/2026-09-09-hermes-context-spill.md
  - docs/roadmap/issue-AR-426-preserve-hermes-hook-specialist-context.md
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0244
type: decision
deciders: [owner]
---

# ADR-0244: Deliver large Hermes card sets through native tools

## Context

Hermes native plugin hooks spill above 10,000 characters. Retained failing turns
lost cards and finalizer guidance while Store counted inline hydration as loading.
The host supports local plugin tools and the existing bridge carries exact native
session/trace correlation.

## Decision

For large Hermes card sets, reserve a bounded hook frame and defer loads until
native tool retrieval. The tool accepts a selected slug, derives correlation from
the host and resolves the exact immutable selected version. Its complete result
must fit below the native tool spill floor before recording loaded evidence.
Recipe version 17 distinguishes this surface from Claude MCP delivery. Existing
inline delivery remains for small sets. Validate the whole Hermes hook envelope.

## Consequences

Full cards and truthful load evidence survive the default hook ceiling. Tool
permission failures and oversized cards remain explicit delivery failures. The
native finalizer still constructs the first visible response; failed receipts are
never reopened. No owner budget, trust or staffing setting changes.

## Alternatives

Increasing or disabling the global spill budget affects other plugins. Reading
spill files violates supplied-code-only requests. Trimming cards destroys exact
version delivery. Relabeling failed terminal receipts would falsify evidence.
