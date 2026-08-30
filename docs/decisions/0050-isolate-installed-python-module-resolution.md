---
title: "Isolate installed Python module resolution from host workspaces"
status: accepted
category: decisions
created: 2026-07-15
updated: 2026-07-15
tags: [python, supply-chain, host-integration, services, security]
related:
  - docs/roadmap/issue-AR-43-isolate-installed-python-module-resolution.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0050
type: decision
deciders: [maintainers]
---

# ADR-0050: Isolate installed Python module resolution from host workspaces

## Context

Agency host integrations and the optional dashboard service intentionally use
the Python interpreter that installed the package. An absolute executable path
protects interpreter selection, but `python -m agency_runtime...` still places
the current working directory on the import path and honors Python path/home
environment variables. Agent hosts commonly run inside untrusted repositories,
so a repository-local package can otherwise shadow the installed runtime.

## Decision

Every generated or registered command that executes an installed Agency module
must invoke the bound absolute interpreter with Python isolated mode (`-I`) and
an absolute package-owned bootstrap script. The bootstrap allowlists executable
Agency modules, restores only the exact installed package parent that owns the
script, and dispatches the fixed module with `runpy`. This retains normal
`pip install --user` compatibility; raw `-I -m` is rejected because isolated
mode deliberately removes the user site that may contain Agency.

Service ownership manifests bind that exact argv. Generated native bridges may
not accept a process-environment override for the Agency Python interpreter;
changing the interpreter requires a deliberate reinstall that regenerates and
revalidates owned artifacts.

This constraint applies to Codex and Claude hooks, Hermes and OpenClaw bridges,
MCP server definitions, dashboard service workers, and future generated Python
entry points. Development commands run directly by a contributor remain outside
the installed-host boundary.

## Consequences

- A hostile workspace package, `PYTHONPATH`, or `PYTHONHOME` cannot replace the
  installed Agency module in a managed integration, while user-site installs
  remain executable.
- Host commands keep the environment-owned interpreter selected at install
  time, consistent with ADR-0040, while module resolution becomes explicit.
- Moving or replacing the interpreter makes ownership state stale and requires
  reinstall or upgrade instead of an implicit environment fallback.
- Tests must exercise hostile working directories and exact generated argv on
  both Windows and Linux-compatible command shapes.

## Alternatives

- Trust the absolute interpreter alone. Rejected because interpreter identity
  does not determine `-m` module identity.
- Sanitize only `PYTHONPATH` and `PYTHONHOME`. Rejected because the current
  working directory still participates in normal module resolution.
- Execute raw `python -I -m agency_runtime`. Rejected because it blocks supported
  user-site installations along with the hostile search paths.
- Import from the current directory after sanitizing environment variables.
  Rejected because it leaves module identity dependent on an untrusted host
  workspace.
- Keep an environment override for emergency interpreter selection. Rejected
  because an inherited host environment is not durable trusted ownership state;
  reinstall is the explicit recovery path.
