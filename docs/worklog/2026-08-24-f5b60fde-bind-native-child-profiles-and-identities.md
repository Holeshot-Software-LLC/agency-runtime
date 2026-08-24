---
title: "Worklog detail: Bind native-child profiles and identities"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [native-child, openclaw, hermes, inference, correlation]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: null
type: worklog
commit: f5b60fde6ad32191aa0a282eea506b2d4c0a6923
short: f5b60fde
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
---

# Worklog detail: Bind native-child profiles and identities

## Purpose

Make OpenClaw and Hermes native-child staffing inherit the exact Agency
inference profile selected for the owning host, and correlate lifecycle
evidence with fields their installed host versions actually emit.

## Approach

The shared native-child boundary now projects `inference.harnesses.<host>` into
the judge configuration while preserving explicit canary pins. OpenClaw staffs
the exact `sessions_spawn` task before execution, binds the accepted child to
the tool-call launch identity, reconciles spawn/end/result races, requires
positive Store receipts, and authenticates nested spawns by the accepted child
session, run, and requester tuple. Hermes indexes child correlation by the
host-issued child session and validates supplied parent, worker, role, and turn
identities before consuming it.

## Challenges encountered

Installed host inspection disproved the generated bridges' assumed fields. An
independent review then found that a fast OpenClaw child could end before its
accepted tool result, that terminal correlation was deleted before durable
recording, and that a blanket child-session bypass skipped nested staffing.
Focused test attempts in group-writable temporary namespaces correctly failed
the repository's cross-account substitution guard; changed-input runs used
umask `0077` and a new private temporary root.

## Decisions and alternatives

ADR-0118, ADR-0153, and ADR-0156 remain authoritative. Native host model routes
stay untouched; only Agency child staffing resolves the host-scoped LiteLLM
profile. Store lifecycle evidence is not promoted into Rule 4 delivery proof,
because OpenClaw and Hermes still lack host-artifact collectors that can create
an immutable `native_child_delivery_verifications` receipt.

## Verification

- Consolidated focused host/profile/security suites: 213 passed, 1 existing skip.
- Full repository Ruff check and format check: passed.
- Documentation metadata, policy availability, worklog, and verification checks: passed after reciprocal dependency metadata was corrected.
- `git diff --check`: passed.
- Two independent review scopes: green after the OpenClaw race, receipt, and nested-authentication repairs.

## Follow-ups

Install Agency only into natively stopped OpenClaw and prove one fresh
operational child over Telegram. Repeat for Hermes only after OpenClaw passes.
Keep Rule 4 unproven until an ADR-0156-compliant host-artifact collector exists.
