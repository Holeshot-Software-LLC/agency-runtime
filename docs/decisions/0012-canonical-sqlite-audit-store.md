---
title: Use SQLite as the canonical audit store with explicit retention
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [storage, audit, retention]
related: []
supersedes: []
superseded_by: null
id: ADR-0012
type: decision
deciders: []
---

# ADR-0012: Use SQLite as the canonical audit store with explicit retention

## Context

Routing, model receipts, specialist loads, delegation events, finalization, and roster governance need a shared source of evidence across hooks and processes. Purely in-memory state disappears on restart and cannot reconcile a final response.

## Decision

Use a local SQLite database as the canonical store for runtime evidence and roster governance. Runtime and audit tables are append-oriented. Provide explicit statistics and trim commands to bound runtime history by age or retained count.

Retention operations may remove runs, receipts, load events, delegation events, worker runs, and finalization events. They must preserve roster sources, quarantined candidates, snapshots, versions, and active agents.

## Consequences

- Hooks and processes can reconcile evidence through a common local store.
- Restarted processes retain relevant session evidence.
- Audit history grows until an operator applies a retention policy.
- Schema changes and session identifiers become durable compatibility concerns.

## Alternatives

- Keep all evidence in process memory. Rejected because restarts and cross-process finalization would lose it.
- Use a remote database service. Rejected as a mandatory dependency for a portable local runtime.
- Automatically delete old records without operator policy. Rejected because silent retention changes weaken auditability.

## Provenance

The store existed from the initial history. Commit 8b377b1 expanded the evidence schema and added bounded trim operations. Commit 901a880 used stored specialist evidence to survive process restarts. The README defines which tables may be trimmed and which governance records are preserved.
