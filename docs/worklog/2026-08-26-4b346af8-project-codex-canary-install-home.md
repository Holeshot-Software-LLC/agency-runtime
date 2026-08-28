---
title: "Worklog detail: Project Codex canary install home"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, installation, native-child, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 4b346af8dae605e6187b292bd46664dad4ab98df
short: 4b346af8
date: 2026-08-26
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
---

# Worklog detail: Project Codex canary install home

## Purpose

The second exact AR-297 Codex container reached the accepted route, created and
completed the fixed child, but recorded no native staffing route, delivery,
grant, or receipt. The current-profile canary marked itself as canary mode while
omitting the explicit owner-home authority required to resolve the immutable
managed installation serving the hook.

## Approach

The current-profile backend now projects its existing source-home authority as
`AGENCY_CANARY_NATIVE_INSTALL_HOME`, normalized to an absolute path. The
install-identity reader remains unchanged and continues to refuse ambient
`HOME` in canary mode, then validates the managed tree, install manifest,
launcher bundle, and running private-runtime digest before admitting delivery.

AR-315 and ADR-0180 record the bounded issue and durable authority decision.
The AR-297 capsule records the exact R2 route, child, finalization, Store and
rollout hashes, and the paired installed-runtime diagnostics.

## Challenges encountered

The native child completed successfully, so parent and child prose alone looked
like a delivery failure. Replaying the restricted parent predicate succeeded;
running the identity check through the installed private runtime isolated the
missing capability. Without it the identity is absent; adding only `/root` as
the explicit owner home yields a current identity with matched candidate and
running runtime digests.

The first documentation command used an interpreter invocation that did not
put the repository package on its import path. The project-interpreter rerun
completed the entire documentation chain successfully.

## Decisions and alternatives

ADR-0180 rejects ambient-home fallback, removing canary mode, accepting a
missing install identity, and redirecting the current profile. The repair
passes explicit authority across the process boundary without selecting a
worker, altering policy, exposing a credential, or adding an activation bypass.

## Verification

- The focused install-identity slice passes 7 warning-strict tests.
- The broader Codex/native-child boundary slice passes 559 warning-strict tests.
- Changed-file Ruff and formatting checks pass.
- Metadata, policy availability, worklog consistency, and all 869-document
  validation checks pass.
- `git diff --check` passes; package-boundary telemetry reports 79.1 percent
  remaining.

## Follow-ups

- Rebuild an immutable exact candidate and require one no-bypass Codex v6
  delivery, consumed receipt, current header, accepted finalization, Store
  correlation, and attestation under AR-297, AR-309, and AR-315.
- Continue the remaining harness, ordinary-process, host/dashboard, gate, and
  teardown packages in the AR-297 capsule after Codex passes.
- Create and link AR-315's tracker issue only after explicit outward-write
  authorization.
