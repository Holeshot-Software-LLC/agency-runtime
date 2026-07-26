---
title: "Do not cache positive filesystem trust without complete authority identity"
status: accepted
category: decisions
created: 2026-07-26
updated: 2026-07-26
tags: [security, filesystem, sqlite, trust, caching]
related:
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/decisions/0052-require-trusted-parents-for-sqlite-store-paths.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
id: ADR-0092
type: decision
deciders: [maintainers]
---

# ADR-0092: Do not cache positive filesystem trust without complete authority identity

## Context

File identity fields such as path, inode/file ID, size, and mtime do not prove
that the owner, mode, DACL, parents, links, or sidecar mutation authority remain
safe. A performance cache keyed only by stable file identity can retain a
positive authorization after permission authority changes.

## Decision

Positive filesystem trust is revalidated at every authoritative connection or
operation boundary unless a cache key and invalidation mechanism includes the
complete platform-specific authority identity and all trusted parents. Current
portable APIs do not provide that complete stable identity, so Store trust is
not positively cached.

Performance work must reduce the number of boundaries through coherent batches
and transactions, not skip trust checks. Negative results may be cached only
when doing so cannot grant authority and recovery behavior is explicit.

## Consequences

- Permission and DACL regressions fail closed without process restart.
- Stable-path hot loops pay a trust check per connection until batching reduces
  connections safely.
- The earlier untracked performance suggestion to cache Store trust by
  path/inode/mtime is rejected.

## Alternatives

- **Cache for process lifetime.** Rejected because process lifetime is not an
  authorization identity.
- **Key by inode and mtime.** Rejected because permission changes can preserve
  both.
- **Accept a time-to-live window.** Rejected because it creates a known
  authorization bypass interval.
