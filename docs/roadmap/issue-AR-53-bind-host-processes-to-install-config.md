---
title: "AR-53: Bind installed host processes to the install config identity"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [configuration, host-integrations, installation, reboot, portability]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-53
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/54
depends_on:
  - AR-38
  - AR-43
  - AR-47
blocks: []
---

# AR-53: Bind installed host processes to the install config identity

## Problem

An install performed with a non-default `AGENCY_CONFIG_PATH` becomes durable
through the dashboard service ownership manifest. If the operator selects
`--no-dashboard`, generated Codex, Claude Code, Hermes, and OpenClaw processes
do not retain that path and can fall back to the conventional config after a
reboot or launch from another environment.

## Current state

Generated subprocesses use the isolated package bootstrap and resolve their
Store through process/default configuration. The dashboard is optional, so its
service manifest cannot be the only durable carrier for host configuration
identity.

## Approach

Add an explicit bounded config argument to the generated hook, MCP, Hermes, and
OpenClaw process commands. Construct every process Store with that identity and
include the path in deterministic bundle fingerprints. Omit the argument only
for programmatic bundles that genuinely have no materialized config path.

## Dependencies

AR-38 establishes service durability, AR-43 isolates package resolution, and
AR-47 freezes each Store identity. This item carries that identity across every
installed host process even when the dashboard is intentionally omitted.

## Acceptance

- [x] All four host bundles embed the exact materialized install config path.
- [x] Hook, MCP, Hermes, and OpenClaw processes construct Stores from that path.
- [x] `--no-dashboard` custom-config installs remain correct after environment removal/reboot.
- [x] Paths with spaces and Windows/POSIX spellings remain inert argv values.
- [x] Bundles without a materialized path retain a safe conventional default.
- [x] Full exact-coverage, Windows/Linux, package, install, and tracker gates pass.
