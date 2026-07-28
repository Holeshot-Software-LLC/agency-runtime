---
title: "Worklog detail: Add immutable attended upgrade discovery"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [updates, cli, dashboard, security, release]
related:
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: e21eab3583fd02e81a10302ee71fe064d454e83d
short: e21eab3
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: Add immutable attended upgrade discovery

## Purpose

Give operators a fast, exact build identity and a low-friction way to discover
the latest release, `main`, or a requested release/ref without granting the CLI,
dashboard, hooks, or MCP an unattended package-mutation path.

## Approach

The implementation separates identity, remote resolution, cached observation,
and application. Mutable GitHub selectors resolve through a repository-bounded
configured `gh` process or fixed-origin HTTPS into a validated full commit SHA.
An owner-private, atomic, cross-process-safe cache feeds cache-only CLI notices
and asynchronous dashboard status. `agency upgrade` prints an exact-SHA pip
command and a separate attended Codex refresh command but executes neither.

The dashboard adds one authenticated `/api/update` observation endpoint and a
strict browser contract that binds status flags, target identities, URLs, and
copy-only behavior. ADR-0107 records the durable authority boundary.

## Challenges encountered

The private repository has no published stable release, Windows Codex refresh
requires genuine operator presence, and startup checks could not be allowed to
slow hooks or consume repeated GitHub access. Three independent closure reviews
also found repository-adjacent executable poisoning, PEP 610 provenance
rebinding, invalid-cache reuse/root divergence, prerelease ordering, and
dashboard resume/schema gaps. Each was repaired before commit with a regression.

## Decisions and alternatives

[ADR-0107](../decisions/0107-resolve-updates-immutably-and-keep-application-attended.md)
keeps update application attended and immutable. Direct self-installation,
dashboard mutation, mutable-ref installation, and synchronous checks on every
CLI startup were rejected.

## Verification

- 58 focused update, CLI, and parser tests passed with warnings as errors.
- Two authenticated dashboard endpoint tests and all 108 dashboard UI tests
  passed, including a real service-to-endpoint-to-browser-validator trace.
- The dashboard resource check passed below the 268 KiB aggregate ceiling.
- Ruff check/format, documentation metadata/policy/worklog validation,
  documentation verification, and `git diff --check` passed.
- Live CLI checks resolved current `main` to an immutable SHA and reported the
  absent stable release truthfully. A temporary authenticated dashboard rendered
  the banner at desktop and 390-by-844 viewports with no console warning/error.
- Security, CLI-contract, and UI-trace reviewers confirmed their findings closed.

## Follow-ups

- Same-repository tracker creation for AR-188 remains pending explicit outward
  authorization.
- Publishing a stable release remains owned by the release process.
- The broader AR-119 attended Codex refresh/canary resumes when the operator
  returns; this commit does not install, trust, push, or dispatch hosted work.
