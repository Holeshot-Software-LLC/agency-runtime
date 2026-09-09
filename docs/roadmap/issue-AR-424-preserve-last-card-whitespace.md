---
title: "AR-424: Preserve the final specialist card bytes in native hook context"
status: open
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [native, context, exact-delivery]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-424
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/812
depends_on: []
blocks: []
---

# AR-424: Preserve the final specialist card bytes in native hook context

## Problem

The shared hook bridge calls rstrip() on preflight context before appending its
contract and header. This removes trailing whitespace from the last selected
card, breaking exact immutable prompt delivery.

## Current state

A four-card regression through the real Zcode hook bridge reproduces the issue:
the first three complete bodies match; the last matches only after stripping.
The adjacent AR-423 owned candidate removes this trim. That candidate is not
part of PR810's production change and is not installed or accepted yet.

## Approach

Preserve the preflight context bytes when joining hook segments. Validate the
final card's exact leading/trailing whitespace through the shared native bridge.
Keep staffing, independent critic, permissions and finalization unchanged.

## Dependencies

AR-423 owns Claude's separate native context-persistence boundary. AR-404 retains
all-host evidence and requires the owned-worktree, PR and merge workflow.

## Acceptance

Repository-required isolated verdicts govern closure after these criteria are judged.

- [ ] Reproduce the final-card byte mismatch through the real hook bridge.
- [ ] Preserve every selected full card exactly, including trailing whitespace,
      without changing inference, critic or finalization policy.
- [ ] Verify the focused shared-host regression and required production checks.
