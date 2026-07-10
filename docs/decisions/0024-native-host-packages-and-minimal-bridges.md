---
title: Package each host integration in its native format
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [adapters, plugins, integration]
related:
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0009-uniform-generated-python-hooks.md]
superseded_by: null
id: ADR-0024
type: decision
deciders: []
---

# ADR-0024: Package each host integration in its native format

## Context

Writing the same Python hook file into every host directory did not prove that each host could discover or execute it. Some hosts require manifests, different directories, a different runtime language, or lifecycle-specific event names.

## Decision

Generate the plugin package and manifest expected by each host. Use Python integration files only for hosts whose native loader supports that format. For a JavaScript plugin host, generate its native package and lifecycle hooks, then invoke the shared Python runtime through a deliberately small JSON bridge.

The bridge accepts structured input, emits structured output, shares the canonical SQLite store, and contains no duplicate routing or evidence logic. Smoke tests validate manifests, syntax, importability, registration, and representative lifecycle behavior.

## Consequences

- A successful install more closely represents actual host loading truth.
- Shared semantics remain in the portable core while native lifecycle wiring remains host-specific.
- Cross-runtime bridges add process and serialization boundaries that require strict error handling.
- Integration claims require host-specific verification, not just file creation.

## Alternatives

- Continue the universal scaffold from ADR-0009. Rejected because format compatibility was an assumption, not verified behavior.
- Reimplement routing in the host's native language. Rejected because it would duplicate the core and weaken parity.
- Support only wrapper commands. Rejected for hosts where native preflight and finalization hooks can provide stronger evidence.

## Provenance

Commit 63b75ee added required manifests for Python plugins, corrected a native plugin directory, generated a native JavaScript package and hook lifecycle, added the minimal JSON bridge, and extended smoke and parity coverage.
