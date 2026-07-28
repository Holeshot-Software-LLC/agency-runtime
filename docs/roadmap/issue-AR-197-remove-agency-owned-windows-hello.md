---
title: "AR-197: Remove Agency-owned Windows Hello"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [windows, security, operator-presence, host-integrations, simplification]
related:
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/handoffs/issue-AR-196.md
  - docs/roadmap/issue-AR-198-install-applicable-suite-by-default.md
  - docs/decisions/0111-install-the-applicable-suite-by-default.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-197
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-185, AR-189, AR-196, AR-198]
---

# AR-197: Remove Agency-owned Windows Hello

## Problem

Agency-owned Windows Hello duplicates harness-native plugin trust, blocks the
core plugin demo behind unrelated service and signing work, and requires a
bespoke protocol for every persistent action. The dashboard-service attempt
proved that the ceremony still cannot make a multi-resource lifecycle atomic.

## Current state

The verifier and its action-specific lifecycle have been removed from current
product and release paths. Exact harness installation uses the harness-native
lifecycle, while roster rollback and owned host uninstall remain fail-closed.
ADR-0111 supersedes only ADR-0110's dashboard opt-in choice: full-suite install
now includes the dashboard unless `--no-dashboard` is supplied. Tracker
creation is pending explicit authorization.

## Approach

Inventory every verifier call site and classify it as routine harness lifecycle
or Agency-owned governance/data mutation. Route routine plugin lifecycle through
the harness's native registration and trust surface. Keep every other positive
mutation fail-closed. Remove the native helper, protocol, provenance, packaging,
distribution, signing, documentation, and tests only after no admitted path
depends on it. Keep dashboard failure isolated from harness activation while
selecting it by default under ADR-0111; `--no-dashboard` remains the opt-out.

## Dependencies

ADR-0110 governs the simplified authority boundary. AR-185 owns the exact Codex
activation canary; AR-189 and AR-196 must not regain positive mutation authority
as a side effect of verifier removal.

## Acceptance

- [x] Codex plugin install/refresh uses Codex-native registration and hook trust
  without Agency-owned Windows Hello or delegation override.
- [x] Other harnesses use only their documented native lifecycle and retain
  truthful enabled/loaded evidence.
- [x] MCP, hooks, broker, and dashboard remain unable to perform persistent
  Agency governance or data mutations.
- [x] Dashboard selection is independent from harness activation and can be
  excluded with `--no-dashboard`.
- [x] All verifier call sites, native assets, build/provenance rules, package
  contents, signing gates, docs, and tests are removed or explicitly retired.
- [ ] Focused install, trust, activation, uninstall-planning, UI, packaging, and
  security tests pass before one fresh live Codex canary.
