---
title: Make CLI delegation bounded and machine-readable
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [delegation, cli, automation]
related: []
supersedes: []
superseded_by: null
id: ADR-0019
type: decision
deciders: []
---

# ADR-0019: Make CLI delegation bounded and machine-readable

## Context

Command-backed delegation can hang indefinitely, and human-oriented child output is difficult for another agent or tool to interpret. The audit store must distinguish a runtime timeout from a backend that exits with the same numeric code.

## Decision

Accept an optional finite positive timeout for CLI delegation. On an actual process timeout, stop waiting, mark the event skipped, store a concrete timeout reason, and return the conventional timeout exit code. If the child itself exits with that code, record failed rather than skipped.

Offer a JSON mode that suppresses child stdout and stderr and emits one structured result containing trace, event, backend, agent, timeout, status, exit code, and error or skip reason when present.

## Consequences

- Automation receives bounded execution and a stable result shape.
- Stored delegation state agrees with the process outcome.
- Quiet JSON mode intentionally hides direct child output; richer capture would need an explicit safe schema.
- Callers must choose a timeout appropriate to the backend.

## Alternatives

- Wait forever. Rejected because one backend can block an entire agent workflow.
- Treat exit code 124 as proof of a timeout. Rejected because a child may legitimately return that code.
- Mix JSON with child output. Rejected because it would make the stream invalid and hard to parse.

## Provenance

Commit 3954d35 added validated timeouts and distinct skipped-versus-failed persistence. Commit d9379f3 added quiet JSON results for success, suggestion, missing executable, timeout, and backend failure.
