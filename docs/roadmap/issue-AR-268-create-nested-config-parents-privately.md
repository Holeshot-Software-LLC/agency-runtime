---
title: "AR-268: Create nested config parents privately"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [configuration, filesystem, security, installer, openclaw, AR-119, AR-264]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/roadmap/issue-AR-266-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-267-accept-openclaw-numeric-package-revision.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-268
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-268: Create nested config parents privately

## Problem

The shared configuration parent helper used `Path.mkdir(parents=True,
mode=0o700)`. POSIX applies that explicit mode only to the final directory;
intermediate components receive the process umask. Under this Linux account's
`0002` umask, the OpenClaw final-only backup path therefore created Agency-owned
intermediate directories as `0775` and immediately rejected them as permitting
cross-account path substitution.

## Current state

- The stopped-host install staged the OpenClaw bundle, then failed before native
  registration at `final_only_delivery_policy`; no gateway restart occurred.
- The newly created `~/.agency-runtime/openclaw` and `config-identities`
  ancestors were `0775`, while the final config-identity directory was `0700`.
  Birth timestamps bind them to this installer attempt rather than historical
  drift.
- The live paths were tightened to `0700` after their unsafe modes and failed
  receipt were preserved.
- A focused regression sets umask `0002`, creates the same three-level backup
  hierarchy, and requires every new component to be `0700`. It failed before
  the repair at the post-create namespace assertion and now passes.
- Tracker creation is pending explicit authorization; no outward-facing write
  is authorized in the current Linux package.

## Approach

Keep the existing pre-create and post-create namespace checks. On POSIX, when
the target parent is missing, reuse Agency's componentwise private-directory
creator, which validates the nearest existing boundary, creates and hardens one
component before descending, and rechecks every identity. Preserve the existing
Windows private-authority path and do not take over a preexisting arbitrary
configuration parent.

## Dependencies

- AR-119 owns truthful installed and live host evidence.
- AR-264 owns the current Linux OpenClaw/Hermes verification package.
- AR-266 and AR-267 repair the preceding stopped-state and stable-version
  compatibility boundaries exposed by the same install.

## Acceptance

- [x] A focused regression first reproduces unsafe intermediate modes under
      umask `0002` and the resulting fail-closed namespace error.
- [x] Every missing POSIX component is created and verified owner-private before
      the next pathname operation.
