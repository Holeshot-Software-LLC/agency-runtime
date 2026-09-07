---
title: "Record AR-183 detached private-mode Linux proof"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, packaging, linux]
related:
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/acceptance/evidence/AR-183-AR-184-private-linux-producer-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 6cc0b17614917389e714375170826e426b50eafd
short: 6cc0b176
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
---

# Worklog detail: Record AR-183 detached private-mode Linux proof

## Purpose

Complete the previously missing Linux producer observation without claiming
native Windows or release-set parity.

## Approach

Use clean detached08fab1c4 under umask077 for the unpatched canonical producer,
strict Twine and independent explicit portable verifier. Record artifact hashes,
sizes, mode census and498 focused passes/one native-Windows skip.

## Challenges encountered

The prior AR407 producer was clean but on a branch, so it did not satisfy the
literal detached-source wording. The fresh detached producer supplies that
evidence. Its inherited merge-ledger error is not a packaging failure; current
publication ancestry already includes that ledger.

## Decisions and alternatives

No policy or runtime change. Preserve same-SHA Windows/Linux equality and
merged-three-file requirements for the owner's Windows machine. Reuse one
portable receipt for both183/184 instead of repeating an identical Linux build.

## Verification

Real builder, Twine and independent verifier exit0. Focused498/one skip40.38s.
Metadata, policy, worklog, docs, strict tracker, Ruff and diff publication checks.
No native host install, provider call or exhaustive gate.

## Follow-ups

AR183 remains in_progress for Windows comparison. Publish, then reconcile184
with this exact shared producer evidence.

Substantive `6cc0b176` records actual detached private-mode Linux evidence, preserving the original acceptance states and Windows-only comparison requirement.
