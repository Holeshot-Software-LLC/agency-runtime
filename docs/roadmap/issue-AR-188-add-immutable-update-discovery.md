---
title: "AR-188: Add immutable update discovery and attended upgrade plans"
status: done
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [cli, dashboard, release, security, operations]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/RELEASE_CHECKLIST.md
  - CHANGELOG.md
  - agency_runtime/core/update_service.py
  - agency_runtime/cli/upgrade_commands.py
  - agency_runtime/server/dashboard.py
  - tests/test_update_service.py
  - tests/test_cli_upgrade.py
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-188
priority: p1
tracker_url: null
depends_on: []
blocks: [AR-190]
---

# AR-188: Add immutable update discovery and attended upgrade plans

## Problem

Operators could print the package version, but they could not establish which
source commit an editable or Git-installed runtime represented, discover a
newer stable release or current `main`, or prepare an exact update without
manually reconstructing repository commands. That slowed repeated development
installs and made version equality easy to confuse with source equality.

A conventional self-updater would be unsafe here. This private prerelease has
no published GitHub release, Codex refresh can require genuine Windows operator
presence, and the dashboard and model-facing surfaces are intentionally denied
persistent package and host mutation authority.

## Current state

`agency -V` and `agency --version` remain fast package-version probes. `agency
version` reports package, install kind, source revision, branch, dirty state,
official-repository identity, and the PEP 610 commit of an exact Git-installed
distribution. `agency version --check` and `agency upgrade check` resolve the
latest stable release, current `main`, one canonical release version, or one
bounded Git ref.

Every remote selector resolves through the configured GitHub CLI first, with a
public HTTPS fallback, under one timeout, bounded responses, a least-privilege
child environment, and strict repository URL/commit validation. Results enter
an owner-private, atomic, concurrency-safe cache. The authenticated dashboard
projects only that validated cache and schedules stale release/main checks in
bounded daemon workers; hook and MCP hot paths never perform update I/O.

`agency upgrade` does not install anything. It converts a resolved target into
an exact commit-pinned package command that the current pip or validated
Agency uv-tool environment can execute, plus a separate Codex refresh command
for an owner-controlled terminal. The dashboard may copy that fixed attended
command, but cannot execute it. Mutable `main` and arbitrary refs are reported as
`different_target` when they differ; they are not called upgrades because
direction cannot be proven without ancestry evidence. Canonical stable releases
alone generate automatic update notices.

The repository currently has no published GitHub release. That is reported as
unavailable rather than silently treating `main` as a release.

## Approach

Keep discovery, resolution, and application separate. Normalize every selector
into a closed-world schema, validate GitHub objects before caching and again
when reading the cache, preserve exact commit identity, and display only fixed
repository URLs and commands. Cache successful observations for 24 hours and
failures for one hour so dashboard startup is non-blocking and routine CLI
startup reads only local data.

Treat update application as an attended external operation. Do not invoke pip,
modify host configuration, restart services, refresh Codex, or weaken native
operator-presence controls from update discovery, the dashboard, hooks, or MCP.

## Dependencies

ADR-0037 and ADR-0099 govern artifact and release identity. ADR-0091 governs
the GitHub CLI process environment. ADR-0096 and ADR-0104 govern persistent
mutation and exact Codex refresh. Tracker creation remains pending explicit
authorization for the outward-facing write.

## Acceptance

- [x] `agency -V` and `agency --version` exit without importing the full CLI.
- [x] `agency version --json` distinguishes package version, exact source
  commit, editable/source/VCS install kind, official origin, and dirty state.
- [x] Release, `main`, canonical-version, and bounded-ref selectors resolve to
  one validated immutable commit under one bounded timeout.
- [x] Private-repository discovery uses configured GitHub CLI authentication
  without forwarding unrelated secrets; public HTTPS fallback is origin- and
  redirect-bound.
- [x] The cache is owner-private, size-bounded, atomic, concurrent-writer safe,
  and revalidates hostile cached text, timestamps, URLs, and commit identities.
- [x] Interactive CLI notification is cache-only, dashboard checks are
  asynchronous, and hook/MCP paths perform no update work.
- [x] The authenticated read-only dashboard traces `/api/update` through strict
  browser schema validation to one inert link and one fixed copy action.
- [x] `agency upgrade` emits environment-usable exact-SHA attended commands,
  fails closed when no installer is proven, and truthfully reports
  `mutation_performed=false`.
- [x] Focused CLI, cache, concurrency, timeout, dashboard API/UI, parser, and
  packaging-budget regressions pass.

## Implementation evidence

Focused validation passes 58 update/CLI/parser tests, two authenticated
dashboard endpoint tests, all 108 dashboard UI tests, and the release-resource
budget check. A live authenticated `main` lookup resolved the repository head
through configured `gh` access and returned the exact immutable commit. A live
authenticated dashboard smoke rendered the update banner at desktop and
390-by-844 viewports with no browser console warnings or errors. No package,
host, trust, tracker, release, or remote repository mutation occurred.

Independent security, contract, and end-to-end trace reviews found and closed
repository-ancestor executable poisoning, installed-provenance rebinding,
unvalidated fresh-cache reuse, fallback-cache divergence, canonical prerelease
ordering, and dashboard lifecycle/cross-field validation gaps before commit.
