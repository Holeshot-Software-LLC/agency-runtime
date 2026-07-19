---
title: "AR-50: Fail closed on invalid runtime environment overrides"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [configuration, environment, validation, fail-closed, security]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-50
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/51
depends_on:
  - AR-48
blocks: []
---

# AR-50: Fail closed on invalid runtime environment overrides

## Problem

Runtime environment overrides accept some malformed values without reporting
the operator error. Invalid numbers can be ignored, dashboard port zero can be
accepted, and an unknown `AGENCY_PROFILE` falls back to standard behavior. A
misspelled `local-only` profile can therefore weaken the intended boundary.

## Current state

Persisted YAML is subject to the strict configuration schema under AR-48, but
the final environment-overlay layer applies permissive parsing and does not
validate every override against the same runtime invariants.

## Approach

Parse every recognized runtime override through a bounded, typed validator.
Reject malformed numbers, ports outside `1..65535`, unknown profiles, and other
invalid override values with a clear `ConfigurationError` before the resulting
configuration reaches storage, routing, or service startup.

## Dependencies

AR-48 establishes strict validation for persisted configuration. This item
extends the same fail-closed contract to the higher-precedence environment
layer required by ADR-0006.

## Acceptance

- [x] Invalid numeric environment overrides fail with `ConfigurationError`.
- [x] Dashboard ports outside `1..65535`, including zero, are rejected.
- [x] Unknown profile names fail closed instead of selecting standard behavior.
- [x] Valid overrides preserve documented precedence and typed values.
- [x] Full exact-coverage, Windows/Linux, package, security, and tracker gates pass.
