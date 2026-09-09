---
title: "Deliver large Claude card sets through versioned MCP retrieval"
status: accepted
category: decisions
created: 2026-09-09
updated: 2026-09-09
tags: [claude, context, immutable-prompts]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
  - docs/worklog/2026-09-09-claude-native-context-delivery.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0241
type: decision
deciders: [owner]
---

# ADR-0241: Deliver large Claude card sets through versioned MCP retrieval

## Context

Claude 2.1.266 persists hook context above 10,000 UTF-16 code units. A real
four-card selection exceeds that bound before its surrounding frame. The caller
prohibits file reads, and the native hook has no established supported override.
Truncating cards would change the immutable prompts selected by inference.

## Decision

Preflight recipe and context policy 16 optionally mark large Claude card sets
for retrieval through the existing agency.load_specialist MCP tool. Keep the
manager frame and exact selected slug/session/trace requests in the hook. Measure
JavaScript string units, reserve room for the contract and header, and fail an
oversized final envelope without accepting the turn.

Selection remains immutable and inference-owned. For marked turns, the tool
resolves only the exact selected version and hash; it cannot substitute the
current active version or an unselected specialist. Existing active-turn and
session checks apply. Record loaded evidence only when the full card is returned.
The initial header therefore excludes pending cards. Preserve every inline card
byte when appending bridge segments, including trailing whitespace.

## Consequences

Large Claude selections require one bounded tool retrieval per selected card.
This can add latency. The native record must prove the actual full responses;
instructions and selected rows alone do not prove model-facing delivery. Existing
finalization policy remains in force: an omitted load stays absent from the
truthful header and cannot satisfy the exact-card acceptance gate. Old recipes
remain readable; ordinary non-Claude tool loading and inline delivery are unchanged.

## Alternatives

Reading a persisted native file violates this caller's scope. Raising undocumented
native thresholds depends on unsupported configuration. Trimming cards changes
selected prompt bytes. Automatically treating selected cards as loaded would
manufacture evidence. These alternatives are rejected.
