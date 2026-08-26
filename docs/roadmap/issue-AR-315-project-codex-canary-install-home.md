---
title: "AR-315: Project Codex canary install-home authority"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, native-child, installation, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/native_child_install_identity.py
  - tests/test_codex_activation_verification.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-315
priority: p0
tracker_url: null
depends_on: [AR-300, AR-309, AR-314]
blocks: [AR-297]
---

# AR-315: Project Codex canary install-home authority

## Problem

The current-profile Codex activation backend marks its process as an Agency
canary but does not project `AGENCY_CANARY_NATIVE_INSTALL_HOME`. The native
child install-identity boundary intentionally refuses ambient `HOME` whenever
canary mode is active. At `SubagentStart`, the accepted fixed route therefore
receives no immutable managed-install identity and staffing fails open before
the configured child judge can run.

## Current state

- Fresh exact `84dd879e` retry R2 reaches accepted route
  `3bac13eb-34f4-4d8a-9973-2170c0f8366e`, creates real child
  `01a04033-0c92-7f91-a9cf-fc89c5a99148`, and completes its fixed work unit,
  but the child receives only the 563-byte identity message.
- Against the exact installed private runtime, the canary environment without
  an owner-home capability resolves no managed Codex identity. Adding only
  `AGENCY_CANARY_NATIVE_INSTALL_HOME=/root` resolves a current identity whose
  candidate and running runtime digests match. Both diagnostics exit 0 with
  empty stderr; their stdout hashes are `550b2048...e3fff` and
  `1fccf6f2...ee60`.
- The bounded repair projects the already authoritative source owner home into
  the current-profile canary environment. The identity reader still validates
  the complete managed tree, install ID, bundle digest, launcher artifacts,
  and running private-runtime digest. No fallback or bypass is introduced.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Use the canary backend's existing source-home resolver to pass one absolute
owner-home capability across the current-profile process boundary, matching
the established isolated-Claude contract. Keep the identity resolver's
canary-mode refusal unchanged so direct hook callers cannot regain ambient
home authority.

## Dependencies

- AR-300 supplies the exact config and current Store to the managed canary.
- AR-309, AR-314, and ADR-0179 supply the exact route, host role, child UUID,
  delivery, and artifact contracts.
- ADR-0173 requires the normal no-bypass managed-policy invocation.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] Exact installed-runtime diagnostics reproduce the missing identity and
      show that the sole owner-home capability restores the immutable identity.
- [x] The current-profile backend projects one absolute owner-home capability
      without changing the isolated host home, config, Store, or trust mode.
- [x] Focused boundary and install-identity tests pass warning-strict (7 tests),
      and the broader Codex/native-child boundary set passes 559 tests; Ruff
      and all 869 documentation checks also pass, each at exit 0.
- [ ] A rebuilt fresh no-bypass Codex transaction writes one v6 child artifact,
      consumes its receipt, and persists the activation attestation or exposes
      a later honest blocker.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
