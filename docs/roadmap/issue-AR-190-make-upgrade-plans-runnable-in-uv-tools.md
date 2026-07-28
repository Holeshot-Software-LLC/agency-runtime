---
title: "AR-190: Make attended upgrade plans runnable in uv tools"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [cli, updates, uv, packaging, security]
related:
  - docs/roadmap/handoffs/issue-AR-190.md
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - README.md
  - CHANGELOG.md
  - docs/TROUBLESHOOTING.md
  - agency_runtime/core/update_service.py
  - tests/test_update_service.py
  - tests/test_cli_upgrade.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-190
priority: p0
tracker_url: null
depends_on: [AR-188]
blocks: [AR-119]
---

# AR-190: Make attended upgrade plans runnable in uv tools

## Problem

The first immutable upgrade planner always emitted
`<current-python> -m pip install ...`. Agency Runtime's supported uv-tool
installation intentionally omits pip, so the command copied from the CLI or
dashboard could not run. The target commit remained correctly immutable and no
mutation occurred, but the plan was not operationally usable in the environment
that owns the installed Agency launcher.

## Current state

Planning now proves which installer the exact executing environment can use.
A stable regular pip entry point inside the exact prefix retains an
interpreter-bound isolated-mode command only after a bounded isolated
`pip --isolated --disable-pip-version-check --version` probe succeeds. A no-pip
environment must contain one stable bounded `uv-receipt.toml` identifying the
Agency Runtime requirement and `agency` entry point; Agency also resolves `uv`
outside repository-controlled roots and proves its no-config tool/bin targets
match that prefix and entry point. Target-changing uv/XDG environment overrides
fail closed. Only then does it print an exact-commit `uv tool install --force
--refresh --no-config` command. A malformed, unrelated, linked, oversized,
unreadable, or missing receipt—or unavailable, unsafe, or misdirected uv
executable—returns an unavailable plan with no command. POSIX uv entrypoint
symlinks are accepted only when their stable executable target is inside the
exact prefix; Windows continues to require the copied non-link launcher.

The planner still performs no install, dashboard mutation, Codex refresh, or
operator-presence action. The operator reviews and runs each command in a normal
owner-controlled terminal.

## Approach

Keep installer selection local and fail closed. Bind pip capability to its
stable entry point inside the exact prefix and invoke it with Python isolated
mode plus pip isolated configuration for both capability proof and the
displayed install. Read the uv receipt
through the shared bounded stable regular-file boundary, accept only the narrow
Agency requirement/entry-point shape, and reuse repository-aware executable
resolution for uv. Preserve the same full immutable Git commit in both pip and
uv plans and retain the separate attended Codex refresh step.
Render Windows commands as inert PowerShell invocations and require the
operator to run each displayed plan unchanged in the same environment.

## Dependencies

AR-188 owns immutable update discovery. ADR-0107 owns the separation between
read-only planning and owner-executed application. Tracker creation remains
pending explicit authorization for that outward-facing write.

## Acceptance

- [x] A pip-capable environment retains an exact-SHA interpreter-bound command.
- [x] A valid Agency uv-tool receipt plus safe uv resolution emits an exact-SHA
  uv-tool command containing no pip invocation.
- [x] A missing, malformed, unrelated, unsafe, or unresolvable uv environment
  fails closed with no command.
- [x] Upgrade planning and the dashboard remain copy-only and execute no package
  or host mutation.
- [ ] Focused update/CLI tests, lint, docs checks, and one live installed uv-tool
  plan pass from the exact final commit.

## Implementation evidence

The recovery candidate passes 65 focused update/CLI tests in 2.68 seconds on
Windows, with one intentional POSIX-only symlink test skipped. Targeted Ruff,
format, and diff checks pass. Repository metadata/policy checks and the full
documentation validator pass for 487 Markdown files. Independent security and
operational rereviews report no remaining blocker in this scope. A bounded
read-only probe using this candidate against the actual uv 0.10.9 installation
selects the expected uv-tool environment and emits valid PowerShell commands.
Exact committed-install and Codex-refresh evidence remain before closure; see
the [active recovery capsule](handoffs/issue-AR-190.md).
