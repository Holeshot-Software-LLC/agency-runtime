---
title: "AR-194: Inspect owned service runtimes across Python versions"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [dashboard, services, python, upgrade, portability]
related:
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/decisions/0050-isolate-installed-python-module-resolution.md
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - agency_runtime/core/launcher_bootstrap.py
  - agency_runtime/core/dashboard_service_core.py
  - tests/test_launcher_bootstrap.py
  - tests/test_dashboard_service.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-194
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-194: Inspect owned service runtimes across Python versions

## Problem

An Agency CLI upgraded under one Python cache tag cannot inspect an owned,
immutable dashboard runtime created under another interpreter. Verification
compares the recorded runtime tag with the inspecting CLI's tag even though the
service manifest intentionally pins its own interpreter and package closure.
The CLI therefore reports a valid owned service manifest as invalid instead of
showing its real inactive or repair-recommended state.

## Current state

The installed uv tool runs CPython 3.10 while the existing owner-scoped
dashboard task and immutable runtime are pinned to CPython 3.13. The 3.10 CLI
reported `private runtime manifest contract is invalid`; the same source under
3.13 validated the task as owned, installed, enabled, inactive, unreachable,
and repair-recommended. The task still points at the older immutable runtime,
so an attended service repair remains necessary after inspection is corrected.
Tracker creation remains pending explicit authorization.

Read-only verification now accepts a self-consistent foreign cache tag while
execution preparation remains current-tag-only. Service installation also
identity-binds and probes the selected trusted Python with fixed shell-free
arguments before preparing a projection, rejecting wrong tags, malformed or
oversized output, nonzero exit, timeout, and executable drift. Seventy-eight
launcher/service-core tests and all 77 dashboard-service tests pass, alongside
the named production, lint/format, documentation, UI, and routing gates.

## Approach

Make read-only verification interpreter-neutral by validating the persisted
interpreter, cache tag, package tree, bootstrap, hashes, paths, and manifest as
one self-consistent immutable closure. Keep preparation and execution strict to
the current interpreter tag so a foreign runtime cannot be constructed or run
through the wrong Python process.

## Dependencies

ADR-0040 preserves the environment-owned launcher identity and ADR-0050 binds
isolated module resolution to the installed package. AR-188 and AR-190 govern
immutable update discovery and executable upgrade plans; neither authorizes an
unattended service rewrite.

## Acceptance

- [x] Read-only verification accepts a well-formed owned runtime pinned to a
  different supported Python cache tag.
- [x] Preparation and execution still reject a foreign, malformed, mismatched,
  or unproven interpreter/tag/runtime combination.
- [x] Dashboard service status reports the real state of a valid cross-version
  owned runtime instead of an invalid-manifest error.
- [x] Focused launcher and dashboard-service tests pass with strict hash, path,
  manifest, and namespace validation retained.
- [ ] An attended owner-side service repair replaces the stale task/runtime and
  a current installed status check reports the new worker reachable.
