---
title: Cut over through a host-specific compatibility shim
status: superseded
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [adapters, portability, historical]
related: []
supersedes: []
superseded_by: docs/decisions/0005-portable-core-thin-host-adapters.md
id: ADR-0004
type: decision
deciders: []
---

# ADR-0004: Cut over through a host-specific compatibility shim

## Context

The first portability cutover needed to reuse a package implementation while a live host plugin still expected older function signatures and retained part of its routing behavior.

## Decision

Introduce a host-specific compatibility module that presents the legacy hook functions but delegates storage, model receipts, specialist evidence, and header formatting to the portable package. Gate use of the portable path behind a runtime flag and retain the old implementation as fallback.

## Consequences

- The package could be exercised incrementally in a live host.
- Two behavioral paths remained available and could drift.
- Host-specific assumptions leaked into the portability boundary.
- Cleanup became necessary once the package proved it could own the full lifecycle.

## Alternatives

- Replace the live implementation in one step. Initially rejected as a higher-risk cutover.
- Keep the compatibility layer indefinitely. Rejected because it would make the host plugin, rather than the package, the actual system of record.
- Move shared behavior into a base adapter and core modules. Adopted by ADR-0005.

## Provenance

Commit 2434f30 introduced the compatibility cutover. The historical handoff explicitly treated it as temporary. Commit 8b377b1 removed the compatibility layer while consolidating evidence behavior.
