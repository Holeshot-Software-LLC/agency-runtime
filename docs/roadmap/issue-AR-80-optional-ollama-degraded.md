---
title: "AR-80: Treat an unavailable optional Ollama fallback as degraded"
status: in_progress
category: roadmap
created: 2026-07-17
updated: 2026-07-18
tags: [doctor, ollama, providers, fallback, operations]
related:
  - docs/decisions/0008-ordered-provider-fallback.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-80
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/83"
depends_on: [AR-05, AR-06]
blocks: [AR-89]
---

# AR-80: Treat an unavailable optional Ollama fallback as degraded

## Problem

`agency doctor` reported a hard failure when the legacy optional Ollama judge
fallback was unreachable even though deterministic routing remained available.
That made a functional starter installation look unusable.

## Current state

The optional legacy fallback now produces a degraded warning and exit code 2.
Explicitly configured provider-chain failures retain their existing hard-fail
semantics. Final branch and merged-install verification remain in progress.

## Approach

Classify health from the configured capability contract: unavailable optional
acceleration is degraded; inability to satisfy an explicitly configured judge
chain is failed. Keep the warning actionable and name the deterministic path
that remains operational.

## Dependencies

AR-05 and AR-06 define provider configuration and authenticated judge paths.

## Acceptance

- [x] An unavailable optional Ollama fallback reports `DEGRADED`.
- [x] The warning states that deterministic token routing remains available.
- [x] Explicit configured-provider failures remain hard failures.
- [ ] Full branch and merged-install doctor gates pass.
