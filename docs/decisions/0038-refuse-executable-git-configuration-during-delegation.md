---
title: "Refuse executable Git configuration during delegated mutations"
status: accepted
category: decisions
created: 2026-07-12
updated: 2026-07-16
tags: [security, delegation, git, portability]
related:
  - docs/THREAT_MODEL.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/roadmap/issue-AR-65-reject-cross-account-executable-namespaces.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0038
type: decision
deciders: [maintainers]
---

# ADR-0038: Refuse executable Git configuration during delegated mutations

## Context

Delegation creates worktrees, stages worker changes, commits successful work,
and may merge predecessor or completed branches. Shell-free Git arguments and a
disabled hook path are necessary but insufficient: repository configuration can
still launch fsmonitor commands, clean or smudge filters, merge drivers,
text-conversion commands, editors, pagers, credential prompts, or inherited
Git environment overrides. Git output can also exhaust memory unless it is
drained through the same bounded process containment as agent backends.

## Decision

Run lifecycle Git commands through the owned, timeout-aware, bounded subprocess
boundary. Strip inherited GIT_* variables; disable global and system
configuration, hooks, fsmonitor, prompts, pagers, editors, signing, and
recursive submodules. Before a mutation that can consult attributes, inspect
local and included configuration by key name only and refuse repositories that
define executable filters, merge drivers, diff commands, or text conversion.
Reject option or inline-configuration injection and preserve fail-closed
worktrees for manual recovery.

## Consequences

- A repository cannot turn Agency Runtime's lifecycle bookkeeping into an
  ambient code-execution path.
- Timeouts, output overflow, and uncertain Git state are explicit failures
  rather than partial successes.
- Repositories using Git LFS or another custom filter, driver, or text converter
  must perform delegation without managed mutations or use a reviewed manual
  workflow. Read-only repository inspection remains supported.
- Global convenience configuration does not influence deterministic lifecycle
  behavior.

## Alternatives

- **Disable hooks only.** Rejected because filters, drivers, fsmonitor, and
  inherited configuration remain executable.
- **Allow a list of common tools such as Git LFS.** Rejected because executable
  locations and versions are local trust decisions that this runtime cannot
  attest portably.
- **Run every repository configuration and rely on the OS sandbox.** Rejected
  because delegation must be safe on hosts without a sufficiently strong
  sandbox and because the runtime itself should not request unnecessary code
  execution.
