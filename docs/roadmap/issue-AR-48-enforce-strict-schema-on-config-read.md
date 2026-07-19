---
title: "AR-48: Enforce the strict configuration schema on every read"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-19
tags: [configuration, validation, fail-closed, security, yaml]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-48
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/49"
depends_on:
  - AR-39
blocks:
  - AR-50
---

# AR-48: Enforce the strict configuration schema on every read

## Problem

Transactional CLI/dashboard writes use a strict schema, but direct
`load_config()` reads can coerce or discard malformed nested values. Examples
such as a mapping where `providers` must be a list, scalar provider entries, or
a scalar observability section can silently materialize defaults.

## Current state

Bounded YAML parsing rejects dangerous syntax and non-mapping roots are being
made fail closed under AR-39. The read path still merges an unvalidated partial
mapping through tolerant dataclass conversion instead of applying the canonical
persisted-document schema.

## Approach

Validate every present file document with the same strict partial schema used
by configuration writes before merging defaults. Keep a missing or
whitespace-only file as the documented empty document. Treat an explicit YAML
`null` as a non-mapping root and reject it, along with unknown fields, wrong
container types, invalid provider entries, and unsafe values, before any Store
or service opens.

## Dependencies

AR-39 establishes no fallback storage on invalid configuration. This item makes
all nested persisted values subject to ADR-0006's typed configuration boundary.

## Acceptance

- [x] Read and write paths share one strict partial-document schema.
- [x] Wrong nested types, scalar provider entries, and unknown fields fail closed.
- [x] Missing and whitespace-only documents retain defaults; explicit YAML null fails closed.
- [x] Invalid configuration cannot create or open a fallback Store/service.
- [x] Full exact-coverage, Windows/Linux, package, security, and tracker gates pass.
