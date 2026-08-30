---
title: "Bind dashboard runtime publication to validated filesystem identities"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-16
tags: [dashboard, security, filesystem, posix, race-condition]
related:
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/roadmap/issue-AR-54-make-dashboard-runtime-publication-swap-safe.md
  - docs/roadmap/issue-AR-66-bind-systemd-unit-to-trusted-xdg-namespace.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0051
type: decision
deciders: [maintainers]
---

# ADR-0051: Bind dashboard runtime publication to validated filesystem identities

## Context

The dashboard publishes a loopback endpoint and bearer token into a private
runtime descriptor so local clients can connect. Path-based lock opening,
permission repair, or atomic replacement can follow or race a substituted
filesystem object when the runtime path is writable by an adversary. Detecting
the mismatch only after a mutation is too late because the unintended target
may already have been modified or received sensitive material.

## Decision

Dashboard runtime locking and descriptor publication must bind every
security-sensitive mutation to a validated filesystem identity. On POSIX, the
runtime directory and lock are opened without following final links, checked
for the expected kind and stable device/inode identity, and repaired through
descriptor-based permission operations. Publication proceeds only while the
validated parent identity remains unchanged, and the published regular file is
revalidated before it becomes authoritative.

Links, reparse points, wrong kinds, inaccessible identities, and substitutions
fail closed. Windows retains its platform ACL implementation but must enforce
the same semantic boundary: an owned private directory, a regular descriptor,
and no accepted identity substitution. Diagnostics must not disclose bearer
material.

## Consequences

- A path swap cannot redirect lock or permission mutations to another object.
- Bearer publication is accepted only in the exact private runtime directory
  validated for this process.
- Runtime startup may refuse an ambiguous or adversarial filesystem layout and
  require the user to repair or remove it deliberately.
- Regression tests must exercise final links, wrong kinds, and substitution
  between validation and mutation on POSIX, plus compatible Windows behavior.

## Alternatives

- Keep path-based `chmod` and detect a mismatch afterward. Rejected because the
  redirected mutation has already occurred.
- Trust atomic replacement alone. Rejected because atomicity does not validate
  the destination directory identity or prevent publication through a linked
  parent.
- Put the bearer token in process environment state. Rejected because it is not
  a durable authenticated discovery channel and can leak through inherited
  process metadata.
- Make the dashboard unauthenticated because it is loopback-only. Rejected
  because local untrusted processes and browser-origin attacks remain in the
  threat model.
