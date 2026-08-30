---
title: "AR-43: Isolate installed Python module resolution from host workspaces"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-18
tags: [supply-chain, python, host-integrations, dashboard, security]
related:
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0050-isolate-installed-python-module-resolution.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-43
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/44"
depends_on:
  - AR-37
blocks:
  - AR-53
  - AR-79
---

# AR-43: Isolate installed Python module resolution from host workspaces

## Problem

Generated integrations invoke an absolute Python interpreter with
`-m agency_runtime`, but do not enable isolated mode. Python can therefore
prepend a host-controlled working directory and honor module-path environment
variables, allowing a hostile workspace to shadow the installed runtime.

## Current state

The interpreter executable is identity-bound, commands avoid a shell, and
child environments are otherwise bounded. Those controls do not establish the
identity of a module resolved by non-isolated Python startup.

## Approach

Run every installed Agency module entry point through an absolute package-owned
bootstrap under Python isolated mode. The bootstrap restores only its exact
installed package parent and allowlists executable Agency modules. Update
service-manifest identity checks, remove environment-controlled interpreter
substitution from installed bridges, and prove a hostile working tree and Python
path cannot replace the packaged runtime. This preserves supported user-site
installs, which raw `python -I -m` would make undiscoverable.

## Dependencies

AR-37 supplies the interpreter-independent Hermes bridge. ADR-0050 makes the
module-resolution boundary uniform for every generated host and service.

## Acceptance

- [x] Generated host, MCP, and dashboard-service Python argv use the package-owned isolated bootstrap.
- [x] Installed bridges cannot select a different interpreter through a hostile workspace environment.
- [x] A subprocess regression proves a shadow `agency_runtime` package is ignored.
- [x] Owned service manifest validation binds the isolated argv exactly.
- [x] Full exact-coverage, Windows/Linux, package, security, and tracker gates pass.
