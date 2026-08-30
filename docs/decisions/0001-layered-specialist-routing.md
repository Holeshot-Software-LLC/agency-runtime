---
title: Use a layered specialist-routing pipeline
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [routing, architecture, resilience]
related: []
supersedes: []
superseded_by: null
id: ADR-0001
type: decision
deciders: []
---

# ADR-0001: Use a layered specialist-routing pipeline

## Context

Specialist selection must be fast for obvious requests, stable within a session, explainable after the fact, and useful even when no model provider is available. A single judge call cannot satisfy all four constraints.

## Decision

Route requests through ordered layers: deterministic companion policy, domain expansion, content-hash cache, session stickiness, confidence bypass, token pre-narrowing, an optional model judge, and a final union of deterministic and semantic selections.

The pipeline returns selected identifiers, confidence, status, and detected work units. Provider failure degrades to token scoring rather than to an empty or silent result.

## Consequences

- Common and repeated requests avoid unnecessary model calls.
- Deterministic policy choices remain visible alongside semantic choices.
- Session state and caching improve latency but must appear in explain receipts.
- Layer ordering becomes part of the routing contract and requires regression coverage.

## Alternatives

- Use only a model judge. Rejected because availability, cost, and latency would determine whether routing works.
- Use only token matching. Rejected because subtle intent and ambiguous specialist boundaries need semantic judgment.
- Select from the entire roster on every model call. Rejected because it increases prompt size and weakens selection quality.

## Provenance

The current README documents the eight-layer contract. The initial repository already contained the layered selector, and later commits c2d1274, dc0be8d, 42f6580, and 31443bc made its fallback, evidence, and policy behavior explicit.
