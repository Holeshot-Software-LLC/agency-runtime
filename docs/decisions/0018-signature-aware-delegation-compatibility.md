---
title: Adapt delegate signatures without masking execution errors
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [delegation, compatibility, errors]
related: []
supersedes: []
superseded_by: null
id: ADR-0018
type: decision
deciders: []
---

# ADR-0018: Adapt delegate signatures without masking execution errors

## Context

Delegate backends expose multiple call signatures: a modern task and workdir shape, a legacy goal and context shape, a task-only keyword, or a positional task. Catching TypeError and retrying another shape cannot distinguish an argument mismatch from a real TypeError raised inside the backend.

## Decision

Inspect the delegate callable signature before invoking it. Bind candidate argument shapes in compatibility order and call the first shape that binds. If the selected backend raises TypeError during execution, preserve it as an execution failure rather than treating it as evidence to retry a different signature.

If a callable does not expose an inspectable signature, invoke the modern shape directly and report any resulting error.

## Consequences

- Legacy and focused delegate callables remain usable.
- Internal backend bugs are not hidden by accidental fallback calls.
- Signature inspection becomes part of the adapter boundary.
- Dynamic callables without introspectable signatures receive less compatibility assistance.

## Alternatives

- Catch every TypeError and retry. Rejected because it masks real backend defects and may execute more than once.
- Support only one signature. Rejected because existing delegation integrations use several stable shapes.
- Require backends to register a signature type separately. Rejected as extra configuration when Python binding can determine compatibility safely.

## Provenance

Commit 4f477f6 replaced exception-driven signature fallback with inspection and binding, and added tests for modern, legacy, task-only, and internal-error behavior.
