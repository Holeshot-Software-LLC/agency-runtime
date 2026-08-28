---
title: "Harden Linux service and verification namespaces"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [linux, systemd, dashboard, packaging, testing, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-301-private-systemd-dashboard-namespace.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
supersedes: []
superseded_by: null
type: worklog
commit: 5c86aae4569f1664f55dcc8ce00d8fbc3b869932
short: 5c86aae4
date: 2026-08-26
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-301-private-systemd-dashboard-namespace.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
---

# Worklog detail: Harden Linux service and verification namespaces

## Purpose

Remove the two local Linux repeatability blockers exposed by AR-297 without
weakening configuration, executable, archive, or service trust. An ordinary
non-root dashboard service must validate the exact config, and documented local
build/test commands must establish their required permissions independently of
the caller's cooperative umask.

## Approach

Non-root and WSL systemd user units now use a systemd-managed mode-0700 runtime
directory for all standard temporary-directory variables and explicitly avoid
the private user namespace that makes host root appear as UID 65534. Root
non-WSL user managers retain `PrivateTmp=true`; the configuration namespace
validator is unchanged.

The canonicalizer admits the observed 0664 ordinary POSIX source-wheel mode only
inside the existing finite source-mode contract and continues to emit 0644.
Pytest establishes/restores a private POSIX umask, creates the shared offline
config at 0700/0600, and validates the exact persistent fixture interpreter once
before the suite fans out.

## Challenges encountered

Systemd's user-service `PrivateTmp` behavior implicitly enables `PrivateUsers`,
so the worker cannot distinguish remapped root from a path genuinely owned by
the overflow UID. The first pytest hook used a noncanonical argument name and
was rejected by Pluggy before collection; the corrected exact hook signature is
covered by the successful focused run.

## Decisions and alternatives

ADR-0176 rejects a UID-65534 trust exception and uses an owner runtime directory
instead. ADR-0177 keeps canonical output and namespace validation strict while
normalizing only the observed safe producer mode and moving permission setup
inside repository-owned test boundaries.

## Verification

- Caller-umask-0002 AR-301/302 focus: 241 passed, two Windows-only attribute
  tests deselected on Linux, exit 0 with warnings as errors.
- Dashboard service/configuration surface: 128 passed, one skipped, exit 0.
- Final changed focus: 151 passed, exit 0 with warnings as errors.
- Unsafe worktree interpreter: one actionable diagnostic, exit 4 in 38 ms.
- Ruff check/format, metadata, policy availability, documentation validation,
  and `git diff --check`: exit 0.
- Trusted decision conformance before this slice: baseline passed, source
  unchanged, 160/160 mutations killed, exit 0.

## Follow-ups

AR-297 still requires the immutable ambient-umask build, named repository spine,
real installed non-root dashboard/authentication proof, and fresh four-harness
container matrix. Tracker parity remains prohibited without separate authority.
