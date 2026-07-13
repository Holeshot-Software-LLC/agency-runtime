---
title: Sanitize errors at the server boundary
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-13
tags: [security, http, errors]
related:
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-15-reliable-json-rejection-responses.md
  - docs/roadmap/issue-AR-19-bounded-overload-responses.md
supersedes: []
superseded_by: null
id: ADR-0017
type: decision
deciders: []
---

# ADR-0017: Sanitize errors at the server boundary

## Context

Unhandled exceptions can contain credentials, prompt fragments, filesystem paths, or backend response data. Returning the raw message to HTTP callers or logging it verbatim turns an implementation failure into an information leak.

## Decision

Return a fixed internal-server-error message for unhandled server exceptions. Log only the request method, normalized path, exception type, and a bounded list of source filename and line references. Do not include the exception message or payload values.

Treat malformed JSON and invalid UTF-8 as client errors with a 400 response rather than allowing them to reach the unhandled-exception path.

## Consequences

- Public error responses do not expose internal values.
- Logs retain enough traceback shape to locate the failing code.
- Some immediate debugging detail is intentionally unavailable and may require local reproduction.
- New server surfaces must use the same boundary discipline.

## Alternatives

- Return exception text to callers. Rejected because exception messages are not designed as safe public output.
- Log full tracebacks and payloads. Rejected because logs are also an exposure boundary.
- Suppress all exception detail. Rejected because exception type and code location provide useful diagnosis without carrying values.

## Provenance

Commit 9e57cf1 introduced fixed 500 responses, value-free error logging, and invalid UTF-8 handling with tests that assert secret-like exception content is absent.
