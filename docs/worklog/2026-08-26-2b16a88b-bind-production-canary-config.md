---
title: "Worklog detail: Bind production canary config"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [canary, configuration, containers, installation]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 2b16a88b
short: 2b16a88b
date: 2026-08-26
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
---

# Worklog detail: Bind production canary config

## Purpose

Make the mandatory Codex production-container canary use the same exact
configuration identity as the installation transaction that created its Store
and native launchers.

## Approach

The installer now passes the resolved config path and configured database path
to its managed-policy canary. `run_canary` carries the optional config identity
to live preparation, which supplies it directly to the evidence Store while
preserving the existing-current requirement. Canaries without an explicit
identity retain their prior default-path behavior. Managed installation fails
closed if either exact identity is absent.

## Challenges encountered

The clean Codex transaction installed the native bundle and managed hook policy,
then exited 1 with `live_attempted=false` and no attestation. Inspection showed
that the installer-created Store was bound to `/etc/agency/agency.yaml`, while
canary preparation reopened the database using the absent default
`~/.agency-runtime/agency.yaml`. That lost only the child-judge pin; no provider
quota was consumed. A broader affected-file test run also reproduced the known
ambient `umask 0002` fixture-boundary refusal; the exact new warning-strict
regressions pass, and the release artifact workflow continues to use a private
umask.

## Decisions and alternatives

No new durable decision was needed; the repair implements ADR-0173's existing
exact-config contract. Activation bypass, an environment-only dependency, and a
copy at the default path were rejected because each would weaken or obscure the
public production-container transaction.

## Verification

- 15 exact AR-299/AR-300 warning-strict regressions passed.
- Ruff check and format check passed for every changed Python file.
- Documentation metadata and canonical validation passed for 844 Markdown
  files.
- `git diff --check` passed.

## Follow-ups

- Rebuild the exact artifacts and all task-owned images from `2b16a88b`, then
  rerun Codex from a newly created clean container under AR-297.
- Create and link the AR-300 tracker only after explicit outward-write
  authorization.
