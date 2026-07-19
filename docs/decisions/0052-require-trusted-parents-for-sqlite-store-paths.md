---
title: "Require trusted parents for SQLite Store paths"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-16
tags: [sqlite, security, filesystem, permissions, trust-boundary]
related:
  - docs/roadmap/issue-AR-62-identity-stable-sqlite-sidecar-trust-races.md
  - docs/roadmap/issue-AR-61-capability-bound-restricted-windows-scratch.md
  - docs/roadmap/issue-AR-56-require-trusted-parents-for-sqlite-store-paths.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/decisions/0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0052
type: decision
deciders: [maintainers]
---

# ADR-0052: Require trusted parents for SQLite Store paths

## Context

SQLite accepts filesystem paths rather than caller-supplied open descriptors.
Validating a path and then calling `sqlite3.connect` cannot exclude a
substitution by another account that can write the parent directory. Agency's
default runtime directory is owner-private, but an explicit database path may
otherwise point into a shared-writable location that the runtime deliberately
does not own or mutate.

## Decision

Agency accepts a Store path only when its immediate parent provides a stable
current-user trust boundary. The default parent is created and maintained as an
owner-private runtime directory. A pre-existing explicit parent is never
silently re-permissioned: it must already be non-link, owned by the current user,
and exclude group, world, or cross-account write access under the platform's
native permission model.

The runtime rejects the path before database creation or schema mutation when
that invariant cannot be proven. Existing database identity is checked before
and after SQLite opens where supported, and read-only inspection does not
resolve through a new path identity. Same-account processes remain inside the
documented local-user trust boundary; Agency does not claim isolation from the
account that owns its configuration, Store, and host integrations.

## Consequences

- Cross-account writers cannot exploit a shared parent to redirect an Agency
  SQLite open after validation.
- Explicit paths in temporary or collaborative directories may be rejected
  until the operator creates a private parent deliberately.
- Agency does not surprise callers by changing permissions on an arbitrary
  pre-existing directory.
- Windows and POSIX use different permission mechanics but enforce the same
  current-user-private semantic boundary.
- Tests must cover safe and shared parents, default creation, links, identity
  changes, and migration of existing private stores.

## Alternatives

- Continue with check-before-connect only. Rejected because a cross-account
  writer can substitute the path between those operations.
- Automatically harden every explicit parent. Rejected because the directory
  may contain unrelated files or be intentionally shared.
- Copy every explicit database into Agency's default directory. Rejected because
  it changes the requested storage identity and can fork durable evidence.
- Claim protection against malicious processes running as the same account.
  Rejected because that account already controls the runtime's config, plugins,
  and storage; it is outside the product's isolation boundary.
