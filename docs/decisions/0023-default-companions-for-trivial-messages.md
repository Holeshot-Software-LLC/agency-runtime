---
title: Load default companions even for trivial messages
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-16
tags: [routing, preflight, companions]
related:
  - docs/worklog/README.md
supersedes: [docs/decisions/0022-omit-preflight-for-trivial-messages.md]
superseded_by: docs/decisions/0045-turn-scoped-specialist-activation.md
id: ADR-0023
type: decision
deciders: []
---

# ADR-0023: Load default companions even for trivial messages

## Context

Trivial classification is still useful for avoiding semantic routing, but it must not bypass deterministic policy. A default action may intentionally require general coordination specialists for every turn.

## Decision

For a trivial message, skip the semantic pipeline but still run deterministic action detection. Resolve the default companion identifiers, filter them against the active roster, record them as loaded for the session, and inject a deterministic preflight context.

Apply the same behavior in shared adapters and the HTTP preflight surface. Revision instructions emitted by header enforcement are control messages and must not be treated as new user requests.

## Consequences

- Trivial turns remain inexpensive while honoring default policy.
- The visible loaded line no longer contradicts deterministic routing.
- Every active default companion can appear on even minimal turns, which is an intentional policy cost.
- Host bridges must recognize enforcement revision instructions to avoid recursion.

## Alternatives

- Continue returning no context for trivial messages. Superseded because it violated policy and evidence invariants.
- Run the full semantic judge for trivial messages. Rejected as unnecessary work.
- Remove default companions. Rejected because default coverage is an explicit governance choice, not a classifier workaround.

## Provenance

Commit badb180 implemented default companion injection for trivial messages in shared adapter and HTTP paths. Commit 63b75ee made the native host bridge ignore revision instructions while preserving trivial-turn default routing.
