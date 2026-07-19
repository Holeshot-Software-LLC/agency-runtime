---
title: "AR-38: Reject non-durable dashboard service environment overrides"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-19
tags: [dashboard, service, environment, reboot, configuration]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-38
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/39"
depends_on: [AR-36]
blocks:
  - AR-53
---

# AR-38: Reject non-durable dashboard service environment overrides

## Problem

The installed dashboard worker persists only `--config`. Process-local database,
port, policy, profile, and related environment overrides can shape installation
but disappear after reboot, silently changing runtime identity.

## Current state

`AGENCY_CONFIG_PATH` is durable because the resolved file is embedded in worker
argv. Other supported runtime overrides are neither embedded nor written to the
config. Agency now checks both the installer process and the systemd user
manager environment, while service metadata and diagnostics expose names only.
Failed manager probes retain their fixed command and return code but replace
both output streams with a redacted diagnostic; allowlisted override names may
still be reported without values.

## Approach

Before any service mutation, detect supported overrides that are not represented
by the persisted config identity and fail with names-only, actionable guidance
to persist safe values through the configuration CLI or dashboard. Continue to
accept explicit config identity and never copy secret values into argv,
manifests, commands, errors, or logs.
For Linux, parse the bounded `systemctl --user show-environment` result and
reject matching Agency or configured credential names before registration,
without returning their values. Apply the same names-only projection to failed
probe streams because systemd or an intermediary can echo environment values
while reporting an error.

## Dependencies

This closes a reboot-durability gap in ADR-0006 and ADR-0029. AR-36 stabilizes
path values inside the persisted config itself.

## Acceptance

- [x] Service install cannot claim durability while relying on transient overrides.
- [x] Explicit `AGENCY_CONFIG_PATH` remains supported and resolves into worker argv.
- [x] Diagnostics expose override names only and no secret values.
- [x] Manager-only systemd overrides block planning, inspection, and installation.
- [x] Windows/Linux service planning, install, rollback, and reboot regressions pass.
- [x] Full exact-coverage, package, and tracker gates pass.
