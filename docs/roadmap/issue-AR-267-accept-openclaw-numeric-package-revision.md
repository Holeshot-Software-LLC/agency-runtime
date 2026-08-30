---
title: "AR-267: Accept OpenClaw numeric package revisions"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [openclaw, installer, versioning, compatibility, AR-119, AR-264]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-267
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-267: Accept OpenClaw numeric package revisions

## Problem

The audited stable Linux host reports `OpenClaw 2026.7.1-2 (0790d9f)`, where
`-2` is a numeric distribution package revision. Agency treated every hyphen
suffix as a semantic prerelease, rejected the supported host after the stopped-
gateway gate passed, and blocked installation with misleading upgrade advice.

## Current state

- The installed host is the explicitly audited 2026.7.x line and satisfies the
  minimum 2026.7.1 patch contract; its gateway remains stopped.
- A changed-precondition install passed launcher identity and then stopped at
  `host_capability_unproven` before any host plugin mutation.
- A focused version-contract regression uses the exact native version string.
  It failed before the parser repair and passes afterward.
- True prerelease, older-line, newer-line, extra-version-component, and unknown
  examples remain rejected by the same focused table.
- Tracker creation is pending explicit authorization; no outward-facing write
  is authorized in the current Linux package.

## Approach

Keep the existing bounded date-version grammar and audited 2026.7 release-line
check. Interpret a hyphen suffix as a stable distribution revision only when
the entire suffix is numeric. Continue rejecting `-rc`, alphanumeric, dotted,
or otherwise prerelease-like suffixes and any unsupported release line.

## Dependencies

- AR-119 owns truthful installed and live host evidence.
- AR-264 owns the current Linux OpenClaw/Hermes verification package.
- AR-285 repairs the preceding stopped-gateway classification boundary.

## Acceptance

- [x] A focused regression first reproduces rejection of the exact installed
      `OpenClaw 2026.7.1-2 (0790d9f)` string.
- [x] A wholly numeric package revision is accepted only on the supported
      2026.7 line at or above patch 1.
- [x] True prereleases, older/newer release lines, extra components, and unknown
      version strings remain rejected.
- [x] The changed checkout passes the focused OpenClaw installer suite.
