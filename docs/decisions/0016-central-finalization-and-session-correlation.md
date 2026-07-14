---
title: Centralize finalization and correlate evidence by session
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [finalization, sessions, evidence]
related: []
supersedes: []
superseded_by: null
id: ADR-0016
type: decision
deciders: []
---

# ADR-0016: Centralize finalization and correlate evidence by session

## Context

Adapters, HTTP, and MCP all need to fill and validate the same visible evidence header. Earlier endpoint code could call a lower-level formatter directly or store caller-provided evidence under a request trace while finalization looked it up by session.

## Decision

Route every interface through the central finalization service. Pass structured trace metadata, host, model, session identity, and the canonical store. Return the full finalization result rather than only formatted text.

Use session identity to associate loaded skills, specialists, and delegations. Preserve a distinct trace identifier for request and finalization-event audit. If only one identifier is supplied, use it as both for backward compatibility.

## Consequences

- Header filling, validation, action, missing fields, and audit events behave consistently across interfaces.
- Multiple traces can contribute evidence to one session without fragmenting state.
- Callers must understand the difference between request trace and conversational session.
- Compatibility logic remains necessary for older callers that send only one identifier.

## Alternatives

- Let every interface format headers independently. Rejected because enforcement and audit behavior would drift.
- Use trace identity for all evidence. Rejected because preflight and finalization traces may differ inside one session.
- Collapse trace and session permanently. Rejected because request-level observability and session-level evidence serve different purposes.

## Provenance

Commit 6dc35cd repaired MCP finalization by calling the central service and returning its structured result. Commit bb0c12d stored HTTP finalization evidence under session identity while retaining trace identity in the response and audit event.
