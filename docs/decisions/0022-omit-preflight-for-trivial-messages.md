---
title: Omit preflight context for trivial messages
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [routing, preflight, historical]
related: []
supersedes: []
superseded_by: docs/decisions/0023-default-companions-for-trivial-messages.md
id: ADR-0022
type: decision
deciders: []
---

# ADR-0022: Omit preflight context for trivial messages

## Context

Short acknowledgements and status pings often do not warrant semantic routing or a model judge call. The initial preflight path classified such messages as trivial and returned before building specialist context.

## Decision

Use length and phrase heuristics to classify trivial messages. Return no specialist preflight context for them and reserve routing enforcement for non-trivial sessions.

## Consequences

- Small acknowledgements avoided semantic routing work.
- Threshold and phrase choices became product behavior.
- Natural short requests such as asking what is next could be misclassified.
- The default companion policy could select required generalists, yet the early return prevented those selections from loading.
- Headers could report loaded none even when deterministic policy said otherwise.

## Alternatives

- Route every message through all layers. Rejected because semantic judging is unnecessary for many acknowledgements.
- Apply deterministic defaults without running semantic layers. Adopted by ADR-0023.
- Keep tuning only the length threshold. Attempted, but proved unable to resolve the policy contradiction.

## Provenance

Commit 901a880 lowered the threshold and persisted non-trivial evidence. Commit be4f52f lowered it again, removed ambiguous phrase patterns, and expanded default companions. These intermediate fixes exposed that the early-return design, not only the thresholds, was the durable problem.
