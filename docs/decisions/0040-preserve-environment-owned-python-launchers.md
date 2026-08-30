---
title: "Preserve environment-owned Python launchers"
status: accepted
category: decisions
created: 2026-07-12
updated: 2026-07-16
tags: [portability, packaging, python, host-integrations]
related:
  - docs/decisions/0050-isolate-installed-python-module-resolution.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0040
type: decision
deciders: [maintainers]
---

# ADR-0040: Preserve environment-owned Python launchers

## Context

Agency Runtime persists its Python launcher in generated host hooks, MCP
manifests, OpenClaw bridges, and user-scoped dashboard services. On Linux, a
virtual environment commonly exposes `bin/python` as a symlink to the base
interpreter. Canonically resolving that symlink changes the persisted command
to `/usr/bin/python` or another base interpreter that does not necessarily have
Agency Runtime installed. Installation can then appear successful while the
host fails only when it invokes the generated integration.

Filesystem paths that identify owned data need canonical resolution for
boundary checks. An environment-owned executable is different: the launcher
path itself carries the selected package environment and is part of the
runtime contract.

## Decision

Convert Python launcher paths to absolute paths without dereferencing symlinks.
Use one shared helper for service and host-payload generation. Generated Codex,
Claude Code, OpenClaw, MCP, and dashboard-service commands must retain the
invoked virtual-environment launcher. Continue resolving data roots where
canonical containment is the security requirement.

Artifact smoke must run outside the checkout with isolated import behavior and
exercise the installed wheel's configuration defaults, packaged dashboard
assets and authenticated loopback health endpoint, real MCP stdio
initialization/tool execution, and generated host bundles on Windows and
Linux.

## Consequences

- Linux virtual-environment installs remain runnable after host registration.
- Windows launchers stay absolute without changing their normal executable
  identity.
- Generated commands remain coupled to the environment that installed Agency
  Runtime; deleting that environment invalidates the integration and requires
  reinstalling it.
- Release CI detects checkout-relative imports and missing package data through
  isolated wheel execution.
- Data-path containment continues to use canonical paths independently of this
  executable-launch policy.

## Alternatives

- **Resolve every executable to its filesystem target.** Rejected because it
  discards the virtual environment that owns the installed package.
- **Always invoke `python` from `PATH`.** Rejected because host processes may
  have a different or attacker-influenced `PATH` and package environment.
- **Copy a private interpreter into every host bundle.** Rejected because it
  increases artifact size, patching responsibility, and platform complexity.
- **Rely only on generated-manifest tests.** Rejected because they cannot prove
  that a clean installed wheel starts its MCP and dashboard surfaces.
