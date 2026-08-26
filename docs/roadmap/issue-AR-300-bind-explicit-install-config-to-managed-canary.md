---
title: "AR-300: Bind the explicit install config to the managed canary"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [canary, configuration, containers, install, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - agency_runtime/cli/install_commands.py
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_proof.py
  - tests/test_cli_coverage_complete_install.py
  - tests/test_canary_coverage_complete.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-300
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-300: Bind the explicit install config to the managed canary

## Problem

The first clean Linux Codex production-container transaction installed its
native bundle and managed hook policy, then exited 1 before a model call. The
installer created the Store from the explicit `--config` path, but the
mandatory managed-policy canary reopened that same database without the path.
The new Store therefore resolved the absent default `~/.agency-runtime/agency.yaml`
and could not find the exact local child-judge pin. The sanitized receipt
reported `live_attempted=false` and `canary child-judge provider pin is
unavailable`.

Using an activation bypass, copying policy into the default path, or depending
on an extra environment variable would weaken the public production-container
contract. The exact configuration and Store identities already known to the
installer must cross the internal canary boundary directly.

## Current state

- `agency install --production-container --config <path>` binds native launchers
  and the managed Codex policy to the requested absolute configuration.
- The canary accepts an explicit Store database path but previously had no
  internal explicit-config argument.
- The managed activation attempt made no model call and persisted no canary
  attestation, so the failed receipt is diagnostic rather than live evidence.
- Tracker creation is prohibited by the active AR-297 task. Tracker parity is
  therefore an explicit unresolved gate.

## Approach

Thread the already-resolved configuration path and configured Store path from
the production install transaction into `run_canary`. Bind that configuration
path when the canary constructs its evidence Store. Keep ordinary standalone
canaries and attended verification unchanged when no explicit path is supplied.
Fail closed if managed-policy verification somehow lacks either identity.

Add focused tests proving both halves of the contract: production installation
passes the exact config/database pair to its canary, and live preparation gives
that pair to the Store while preserving `require_existing_current`.

## Dependencies

- ADR-0173 owns the durable managed-policy install and mandatory normal-launch
  canary contract.
- AR-297 owns the clean-container retry and later unattended invocation proof.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] Managed installation passes the exact resolved configuration and Store
      paths to its mandatory canary.
- [x] Canary Store preparation binds the explicit configuration identity and
      keeps the current-existing Store requirement.
- [x] Standalone canaries without an explicit path preserve their current
      default configuration behavior.
- [x] Focused regression, child-judge, Ruff, and formatting checks pass.
- [ ] A rebuilt clean Codex container completes the production transaction and
      records the pinned requested/actual local judge identities.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.

## Verification evidence

The rebuilt candidate reaches live managed-canary staffing twice with the exact
configuration SHA-256
`cb569bf027133305df594d8ff029dffb8d38f545e960517d4431dfbf1b2bc2e1`,
instead of repeating the prior absent-default-config failure. Both attempts
then exit 1 at `staffing_critic_rejected`; neither records the required child
judge or persistent attestation. This is positive evidence for the bounded
config-forwarding repair but not completion of the container acceptance item.
