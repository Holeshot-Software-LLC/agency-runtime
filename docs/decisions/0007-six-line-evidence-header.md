---
title: Enforce a six-line response evidence header
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-16
tags: [observability, evidence, contracts]
related:
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0045-turn-scoped-specialist-activation.md
id: ADR-0007
type: decision
deciders: []
---

# ADR-0007: Enforce a six-line response evidence header

## Context

Routing suggestions, specialist loads, delegation calls, and model selection are otherwise invisible in a final response. A header that merely repeats planned behavior would be misleading; it must be reconciled with recorded events.

## Decision

Every enabled host finalizes visible responses into a six-line header covering loaded specialists, delegated specialists, loaded skills, actual model, rationale, and outcome influence.

Run routing preflight for work turns regardless of provider health. Capture skill and specialist loads from tool events. Before completion, validate the header and require it to agree with canonical session evidence. A bare loaded-none or delegated-none claim is rejected when recorded evidence or an open delegation opportunity contradicts it; a concrete blocker may be surfaced instead.

## Consequences

- Operators can inspect evidence without opening the database first.
- Finalization and pre-verification are correctness boundaries, not cosmetic formatting.
- Tool naming and session correlation must remain consistent across hosts.
- Retry prompts must avoid recursively becoming new user work.

## Alternatives

- Trust the model to self-report its behavior. Rejected because self-reports routinely diverged from actual tool and store evidence.
- Emit a separate debug log only. Rejected because the final user-visible artifact would remain unaccountable.
- Skip preflight when a preferred provider is healthy. Rejected because provider routing and specialist-loading context are different responsibilities.

## Provenance

Commit 5eb4de1 added model-group complexity to the header. Commit 886d6cf captured specialist loads in addition to skills. Commit c2d1274 made routing preflight unconditional for work turns and added pre-verify enforcement. Commit 8b377b1 consolidated the contract across adapters.
