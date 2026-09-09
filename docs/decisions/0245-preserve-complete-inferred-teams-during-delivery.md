---
title: "Preserve complete inferred teams during delivery"
status: accepted
category: decisions
created: 2026-09-09
updated: 2026-09-09
tags: [delivery, reliability, workforce]
related:
  - docs/roadmap/issue-AR-427-preserve-complete-inferred-specialist-team.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0245
type: decision
deciders: [owner]
---

# ADR-0245: Preserve complete inferred teams during delivery

## Context

The native Claude routing receipt selected five specialists, including a security
reviewer. Preflight passed that team to a legacy helper capped at four, persisted
only four prompt references and later accepted the response. The preflight
contract says staffing controls team size, but hydration imposed a second cap.

## Decision

Preflight requests complete-team hydration. Use the existing durable sixteen-card
reference ceiling, preserve selection order, and require the delivered references
to equal the complete selected set before recording any load. Missing cards,
reference overflow or whole-context overflow fail explicitly. Keep existing host
context limits and per-card ceilings. Legacy helper callers retain their existing
four-card default unless they request complete-team semantics. Recipe 19 separates
fresh policy from older immutable receipts; no old receipt is reopened.

## Consequences

An assurance worker cannot silently disappear after verified staffing. Larger
teams may fail their existing host context limit, which remains a visible failure
rather than partial successful delivery. Claude MCP and Hermes callback delivery
receive every selected reference admitted by the same complete-team check.
All five native host paths use the shared preflight rule.

## Alternatives

Increasing global context/output budgets changes unrelated behavior. Reordering
or choosing a smaller team in hydration would replace inference authority.
Counting omitted cards loaded would falsify evidence. All are rejected.
