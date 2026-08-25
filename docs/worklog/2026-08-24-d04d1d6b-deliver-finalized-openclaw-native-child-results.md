---
title: "Worklog detail: Deliver finalized OpenClaw native-child results"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, native-child, finalization, delivery, security]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/decisions/0170-authorize-finalized-openclaw-child-announcements.md
supersedes: []
superseded_by: null
type: worklog
commit: d04d1d6bdd2884b20ed9298a9fb6e8f05c8db257
short: d04d1d6b
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
---

# Worklog detail: Deliver finalized OpenClaw native-child results

## Purpose

Let OpenClaw return one finalized native-child result through its required
message-tool completion turn without weakening Agency's Store-backed parent
finalization, while keeping host configuration and protected harnesses
unchanged.

## Approach

The OpenClaw bridge now retains each accepted `sessions_spawn` completion
identity, prepares a dedicated message-tool-only context from the exact parent
trace, and revalidates the requester, parent, worker, native run, launch, work
unit, and reciprocal Store joins immediately before delivery. Only one
text-only implicit-target message whose canonical payload matches the
authoritative parent terminal receipt receives the existing one-use dispatch
marker. The later child-end callback reconciles exact durable lifecycle state
without replacing the parent terminal event.

OpenClaw's child process deadline now encloses the harness-scoped Agency judge
timeout. Provider selection remains host-scoped for both hosts, but Hermes
retains its prior judge and installed-hook deadlines.

## Challenges encountered

The retained live failure showed that OpenClaw completes its requester-side
announcement before emitting `subagent_ended`, so the end callback cannot
authorize delivery. Independent review also found that an orphaned or
conflicting `announce:v1:` hook identity could fall through to ordinary
preflight. The final bridge uses the host-owned prefix only for denial, never
splits it to recover identities, and blocks both event/context mismatch
directions before any synthetic run or inference evidence can be created.

Validation attempts from the group-writable temporary worktree correctly
failed interpreter trust checks. Changed-input runs used the repository's
trusted system interpreter for the fast spine and an owner-private copied
interpreter plus umask `0077` for the curated mutation gate.

## Decisions and alternatives

ADR-0170 records the completion authority boundary. Finalizing a synthetic
announcement trace, trusting prompt prose, allowing arbitrary message-tool
targets, sending directly from Agency, or parsing colon-delimited identities
were rejected. Operational parent delivery remains distinct from ADR-0156
Rule 4 child-card delivery proof.

## Verification

- Focused OpenClaw/native-child/profile/security suites: 299 passed, 1 existing skip.
- Named fast Python production spine: 848 passed, 3 existing skips.
- Curated decision-conformance evaluation: 151 of 151 mutations killed; baseline passed.
- Dashboard UI: 134 passed; routing evaluation: passed.
- Full Ruff check and format check: passed.
- Documentation metadata, policy availability, worklog, and verification checks: passed.
- `git diff --check`: passed.
- Independent security review: green with no remaining Critical or High finding.

## Follow-ups

Install Agency only into natively stopped OpenClaw and prove a fresh Telegram
native-child completion with correlated Store/provider/lifecycle evidence.
Only after OpenClaw passes, perform the equivalent Agency-only Hermes proof.
Rule 4 remains unproven until an ADR-0156-compliant host artifact exists.
