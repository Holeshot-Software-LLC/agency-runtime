---
title: "AR-36: Make configured file paths independent of process CWD"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [configuration, paths, portability, reboot, storage]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-36
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/37"
depends_on: [AR-28]
blocks:
  - AR-38
  - AR-39
  - AR-40
---

# AR-36: Make configured file paths independent of process CWD

## Problem

Relative `store.db_path` and `companion_policy_path` values resolve against each
process working directory. CLI, dashboard-service, and host-hook processes can
therefore use different state after reboot even though they share one config.

## Current state

The config file itself has a canonical durable identity, but its path-valued
fields are expanded only when a consumer uses them. Task Scheduler, systemd,
terminals, and native hosts do not promise the same working directory.

## Approach

Resolve relative persisted paths against the canonical config file directory
when loading typed configuration. Preserve absolute and home-relative behavior,
and apply the same rule to the custom companion policy. Prove CLI, service, and
hook consumers launched from different CWDs select the same files.

## Dependencies

This completes ADR-0006's single-config boundary and builds on AR-28's durable
configuration identity without changing precedence.

## Acceptance

- [x] Configured database and policy identity is stable across CWD and reboot.
- [x] Explicit and default config paths behave identically on Windows and Linux.
- [x] Environment overrides have explicit, documented path semantics.
- [x] Full exact-coverage, package, and tracker gates pass.
