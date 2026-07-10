---
title: "AR-06: Implement CLI-authenticated judge providers"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [providers, authentication]
related:
  - docs/decisions/0008-ordered-provider-fallback.md
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-06
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/6"
depends_on: [AR-05]
blocks: [AR-07]
---

# AR-06: Implement CLI-authenticated judge providers

## Problem

Users who already authenticate through a supported local model CLI cannot currently use that authenticated session as a routing judge. Requiring a separate API key adds setup friction and makes the documented `cli` provider type misleading.

## Current state

`ProviderEntry` recognizes `type: cli` and reports its authentication method as OAuth, but the judge runtime only performs HTTP requests and skips non-local providers without a resolved API key. Host CLI binaries are detected for adapter and delegation use, not as judge providers. No CLI judge transport, timeout contract, response normalization, or fallback test exists.

## Approach

Define a narrow provider transport contract and implement explicit CLI-backed providers only where a stable, non-interactive JSON invocation is available. Normalize output into the same selection result used by HTTP providers, enforce timeouts and bounded output, redact command diagnostics, and continue through the fallback chain on unavailable auth, malformed output, or process failure.

## Dependencies

Depends on `AR-05` so CLI-authenticated entries can be configured and validated without hand-editing YAML.

## Acceptance

- [ ] At least one supported CLI-authenticated provider completes a judge selection without an API key.
- [ ] Provider detection distinguishes an installed binary from a usable authenticated session.
- [ ] Invocation is non-interactive, time-bounded, output-bounded, and secret-safe.
- [ ] Failures fall through to the next configured provider and ultimately to deterministic token routing.
- [ ] Unit and integration tests cover success, missing authentication, timeout, invalid JSON, and fallback order.
