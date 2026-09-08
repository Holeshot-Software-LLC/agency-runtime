---
title: "AR-194: Inspect owned service runtimes across Python versions"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-09-07
tags: [dashboard, services, python, upgrade, portability]
related:
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/handoffs/issue-AR-194.md
  - docs/roadmap/acceptance/evidence/AR-194-service-runtime-reconciliation-20260907.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
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

The July report concerned a Windows CPython-3.10 CLI inspecting an older
CPython-3.13 task/runtime. That historical machine state is not the current
Linux installation. Its original repair evidence remains unverified, not a
reason to repair the healthy Linux service or recreate a presence verifier.

Read-only verification now accepts a self-consistent foreign cache tag while
execution preparation remains current-tag-only. Service installation also
identity-binds and probes the selected trusted Python with fixed shell-free
arguments before preparing a projection, rejecting wrong tags, malformed or
oversized output, nonzero exit, timeout, and executable drift.

On source `f408b6f2`, fresh focused launcher/service-core/service tests pass:
116 passed, 42 deselected in 2.75 seconds. This Linux-safe selection includes
foreign-platform fixtures, not native Windows execution. The installed owner
CLI's read-only status exits zero and reports a current, owned, enabled,
active, reachable Linux systemd service with no repair recommended. Its four
inspection/CLI modules match this source byte-for-byte; the worker remains
pinned to runtime `4329d760`. This is not whole-main installation proof or a
fresh service-repair demonstration. Exact output and limits are in the
[portable receipt](acceptance/evidence/AR-194-service-runtime-reconciliation-20260907.md).

ADR-0117 already replaced AR-196's separate human-presence premise. Normal
owner CLI authority can perform supported service repair; ownership, launcher
identity and postconditions remain required. AR-196 is historical context,
not an implementation dependency. Native Windows repair/reachability evidence
remains the only unsupported original acceptance clause. No verdict or done
state is asserted. This legacy record remains pre-tracker exempt.

## Approach

Make read-only verification interpreter-neutral by validating the persisted
interpreter, cache tag, package tree, bootstrap, hashes, paths, and manifest as
one self-consistent immutable closure. Keep preparation and execution strict to
the current interpreter tag so a foreign runtime cannot be constructed or run
through the wrong Python process.

## Dependencies

ADR-0040 preserves the environment-owned launcher identity and ADR-0050 binds
isolated module resolution to the installed package. AR-188 and AR-190 govern
immutable update discovery and executable upgrade plans. ADR-0117 governs
owner-directed service mutation; this evidence package authorizes and performs
inspection only. AR-196 was superseded by AR-204 and is not a pending verifier
implementation prerequisite.

## Acceptance

The original five criteria and checkbox states below are preserved verbatim.
In criterion 5, "attended" records the superseded July authority premise, not
a current second-presence requirement. The meaningful remaining requirement is
native owner-CLI repair of the stale Windows task/runtime and a reachable
installed worker; the Linux status receipt does not satisfy that requirement.

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
