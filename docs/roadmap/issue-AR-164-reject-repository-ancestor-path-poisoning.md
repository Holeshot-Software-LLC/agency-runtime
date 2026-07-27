---
title: "AR-164: Reject repository-ancestor PATH poisoning"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [security, processes, executables, delegation, git]
related:
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/THREAT_MODEL.md
  - SECURITY.md
  - agency_runtime/core/process_argv.py
  - tests/test_executable_discovery_security.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-164
priority: p0
tracker_url: null
depends_on: [AR-60]
blocks: []
---

# AR-164: Reject repository-ancestor PATH poisoning

## Problem

Executable discovery excluded only the exact working directory or an explicitly
supplied target root. From a nested working directory such as `repo/src`, a
hostile sibling `repo/bin` entry remained eligible on `PATH`. The first Git
invocation used to discover the repository root and several non-delegation
launch surfaces could therefore select repository-controlled code before the
full target boundary was known.

## Current state

One inert filesystem-marker walk now derives the exact working directory and
every repository ancestor without executing Git, hooks, or repository
configuration. Discovery and final artifact validation use that same forbidden
root set. Explicit argv paths, one-argument resolver results, Windows
case/PATHEXT wrapper variants, and link aliases into a repository fail closed;
ordinary absolute `PATH` entries outside a repository remain eligible.

The contract is applied to direct Codex execution, generic command delegation,
the first lifecycle Git call, native installation, dashboard service-manager
commands, and smoke-test Node discovery.

## Approach

Centralize inert repository-boundary discovery beside executable resolution.
Filter every repository descendant from `PATH`, then independently reject the
final lexical and resolved candidate under the same roots. Preserve final
identity freezing and immediate pre-spawn revalidation so the change closes
the discovery gap without weakening AR-60's replacement-race controls.

## Dependencies

AR-60 and ADR-0055 own executable identity, namespace, and pre-launch
revalidation. AR-164 strengthens their repository boundary from exact working
directory to inertly discovered repository ancestors.

Tracker creation remains pending owner authorization; no outward tracker write
was performed in this local implementation session.

## Acceptance

- [x] Nested working directories exclude sibling repository `PATH` entries.
- [x] The first Git root-discovery invocation cannot select repository Git.
- [x] Explicit argv and one-argument resolver results inside a forbidden root fail closed.
- [x] Windows path spelling, case, PATHEXT wrappers, and resolved link aliases cannot bypass the boundary.
- [x] Direct Codex, command backend, installer, dashboard, and smoke launch paths use the shared contract.
- [x] Absolute non-repository `PATH` discovery remains supported.
- [x] Focused tests, Ruff, documentation validation, and diff validation pass.

## Implementation evidence

The executable-discovery security suite passes 37 tests with one platform
symlink skip. Command/CLI delegation passes 64 tests, delegation backends pass
69, native installer passes 114, smoke isolation/coverage passes 33, and the
affected dashboard service core passes 47. Focused Ruff, documentation
validation across 422 Markdown files, and scoped `git diff --check` pass. Full
repository integration and tracker creation remain outside this local slice.
