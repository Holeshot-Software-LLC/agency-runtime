---
title: "Worklog detail: Failed Codex activation proof"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [production-readiness, codex, installation, canary, operator-presence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: worklog
commit: dfe6f46
short: dfe6f46
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
---

# Worklog detail: Failed Codex activation proof

## Purpose

Replace registered/enabled inventory inference with exact normal-profile Codex
activation and reinstall evidence after the owner requested a visible Agency
installation in the active Codex environment.

## Approach

Inspect current source and artifact status, run the candidate's write-free Codex
install plan, execute the exact-confirmed current-profile canary, and then invoke
the supported installer once. Keep inventory, live participation, and mutation
postconditions separate.

## Challenges encountered

The pre-existing plugin is registered and enabled, but its managed bundle is
older than candidate `29da6eca`, launcher evidence has drifted, hook trust is
unverified, and loaded state is unknown. The current-profile invocation exited
successfully at the host layer but emitted none of the required Agency header
or correlated runtime evidence. Generic install has no production operator-
presence verifier and therefore rejected before dispatch.

## Decisions and alternatives

Do not copy candidate files into the managed marketplace, edit Codex's native
registry, or grant hook trust directly. Those alternatives bypass the AR-143
prepared-mutation and Codex-owned trust boundaries. Preserve the failure and
implement the prepared install coordinator before extending the native helper.

## Verification

- Pushed `main` at `880a5ce` passed the named 521-test production spine with 5
  platform skips, all 105 UI tests, Ruff, formatting, docs, and routing eval.
- Current-profile canary: exit 1; no Agency header, specialist, correlated
  route, receipt, finalization, or persisted attestation.
- Candidate install dry-run: complete; backup and stale bundle refresh planned.
- Candidate real install: exit 1 with operator presence unavailable; no
  persistent change dispatched.
- Documentation validation passed for 449 maintained Markdown files.

## Follow-ups

- [AR-143](../roadmap/issue-AR-143-require-operator-presence-for-controls.md):
  implement a prepared, frozen, replay-safe Codex install coordinator before an
  enumerated native install presence operation.
- [AR-161](../roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md):
  preserve the signed-delivery and attended-canary gates.
