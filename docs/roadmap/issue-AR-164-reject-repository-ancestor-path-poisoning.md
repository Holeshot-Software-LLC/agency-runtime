---
title: "AR-164: Reject repository-ancestor PATH poisoning"
status: done
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [security, processes, executables, delegation, git]
related:
  - docs/roadmap/acceptance/issue-AR-164.md
  - docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
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

AR-187 now separates repository-independent host lifecycle CWD isolation from
this marker-derived repository boundary. Native commands retain every actual
repository ancestor while using a private launch directory, so a broad
non-repository caller such as the user's home does not become a false recursive
repository root.

The contract remains applied to the first Git call, current CLI-provider
inspection/inference, native installation, dashboard service-manager commands
and smoke-test Node discovery. Job B removed the old Agency-owned direct host
execution and generic command backends in fb34191f; they are not restored.
ADR-0227 explicitly reconciles only criterion 5 to these current surfaces.
Fresh discovery/launch/Git tests pass 38, 129 and 24 cases respectively. No code
or test change was needed. First isolated review at 083ae8b5 satisfies criteria
1–4 and 6–7. Criterion 5 is absent: current launch integrations are demonstrated,
but the retirement claim needs an actual candidate tree listing rather than a
description. All first verdicts remain preserved at 6ac3b1aa. The correction
adds actual full candidate-directory and deletion-status output; no criteria,
runtime or test changes. All seven current criteria satisfy at 2a7c20c5 in the
second and final isolated review. AR-164's scoped record is complete; native
Windows qualification and AR-187 attended activation remain separate.

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

AR-347's governed pre-tracker exemption applies; no duplicate tracker is needed.
Native Windows and AR-187's attended activation remain separately owned work.

## Acceptance

- [x] Nested working directories exclude sibling repository `PATH` entries.
- [x] The first Git root-discovery invocation cannot select repository Git.
- [x] Explicit argv and one-argument resolver results inside a forbidden root fail closed.
- [x] Windows path spelling, case, PATHEXT wrappers, and resolved link aliases cannot bypass the boundary.
- [x] Current CLI-provider, installer, dashboard, and smoke launch paths use the shared contract; retired Agency-owned execution backends remain absent.
- [x] Absolute non-repository `PATH` discovery remains supported.
- [x] Focused tests, Ruff, documentation validation, and diff validation pass.

## Requirement reconciliation

ADR-0227 preserves the original fifth criterion here: "Direct Codex, command
backend, installer, dashboard, and smoke launch paths use the shared contract."
The deliberate Job B removal is recorded in AR-236 and follows native-host
ownership. Current CLI-provider inference is not an Agency-owned worker backend.
Criteria 1–4 and 6–7 remain unchanged. Historical checked boxes are preserved in
Git; the current record has seven new isolated satisfied verdicts at 2a7c20c5.

Windows spelling/case/PATHEXT algorithms are exercised as portable simulations
on Linux, alongside real Linux symlink rejection. No native Windows execution,
PowerShell companion, filesystem/ACL certification or host activation is claimed.

## Historical implementation evidence

The executable-discovery security suite passes 37 tests with one platform
symlink skip. Command/CLI delegation passes 64 tests, delegation backends pass
69, native installer passes 114, smoke isolation/coverage passes 33, and the
affected dashboard service core passes 47. Focused Ruff, documentation
validation across 422 Markdown files, and scoped `git diff --check` pass. Full
repository integration and tracker creation remain outside this local slice.

## Current verification evidence

The [September 7 receipt](acceptance/evidence/AR-164-executable-boundary-20260907.md)
records 38 discovery passes/one native-Windows deselection (0.14s), 129 current
launch passes/23 Windows-named deselections (3.39s), and 24 surviving Git/process
passes/three Windows-named deselections (0.63s), all warning-strict with no skips
or failures. Product/test/script/config bytes match fcdcd6eb; the named spine
1085/three existing skips and unchanged 188-case DOM result are explicitly reused.
No exhaustive diagnostics, new native Windows execution or trust bypass.
