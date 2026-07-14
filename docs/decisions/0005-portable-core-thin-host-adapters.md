---
title: Keep a portable core with thin host adapters
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [architecture, adapters, portability]
related: []
supersedes: [docs/decisions/0004-host-specific-compatibility-shim.md]
superseded_by: null
id: ADR-0005
type: decision
deciders: []
---

# ADR-0005: Keep a portable core with thin host adapters

## Context

Routing, evidence, receipts, finalization, and storage must behave consistently across multiple agent hosts. Vendored or host-local implementations make fixes uneven and turn the live installation into the only authoritative copy.

## Decision

Keep shared behavior in the installed Python package, primarily in core modules and BaseAdapter. Host adapters translate native events into that contract and expose only genuinely host-specific operations. Generated host files import the package rather than vendoring runtime logic.

Compatibility shims are transitional, not permanent architecture. Availability checks use in-process executable lookup instead of spawning a shell command.

## Consequences

- Evidence parity can be tested once across host adapters.
- A package update fixes shared behavior without copying code into every host directory.
- Host integrations remain responsible for correct native lifecycle wiring.
- Cross-language hosts may need a deliberately small bridge to the shared core.

## Alternatives

- Maintain a complete implementation per host. Rejected because behavior and schemas would diverge.
- Make one host plugin the canonical runtime. Rejected because portability is a primary product constraint.
- Force every host to load the same plugin format. Rejected later for hosts with different native plugin systems; see ADR-0024.

## Provenance

Commits 3b39f58 and 8b377b1 established the package as the live system and consolidated common behavior. Commit 2235d7e removed shell-spawned availability probes. Commit 63b75ee preserved the thin-core boundary while adding a native cross-language bridge.
