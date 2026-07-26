---
title: "AR-130: Revalidate Store trust at authoritative boundaries"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [security, sqlite, filesystem, trust, performance]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0092-do-not-cache-positive-filesystem-trust.md
  - agency_runtime/core/store/sqlite.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-130
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-130: Revalidate Store trust at authoritative boundaries

## Problem

Positive SQLite storage trust is cached by a path identity that does not change
when directory permissions or DACL authority changes. A trusted result can
therefore survive a later loss of the property it authorizes.

## Current state

A reproduced same-inode/same-mtime permission transition returned trusted
before and after the transition and invoked the authoritative trust check only
once. The existing untracked audit draft recommends this cache as a performance
optimization; that recommendation is explicitly rejected by current evidence.

## Approach

Remove positive authorization caching or bind it to a complete authoritative
permission fingerprint and revalidation contract. Recover latency through
transaction batching and coherent request scopes, never by reusing stale trust.

## Dependencies

ADR-0092 governs filesystem trust caching. AR-133 owns transaction batching.

## Acceptance

- Changing relevant POSIX mode, owner, Windows DACL, parent identity, or link
  state invalidates prior trust without restarting the process.
- Every Store connection fails closed after a trust regression.
- Stable-path regression tests cover same-inode and same-mtime transitions.
- Performance remains within the measured hook budget through safe batching.

## Implementation evidence

Positive trust caching has been removed. Every Store connection re-runs the
authoritative platform check, including same-inode/same-mtime authority
regressions. Focused Store security suites and the combined checkpoint suite
pass. The measured Windows connection cost remains visible; AR-133 must recover
it through transaction batching before this item's performance acceptance can
close.
