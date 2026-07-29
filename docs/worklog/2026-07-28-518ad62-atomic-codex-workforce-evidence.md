---
title: "Worklog detail: Restore atomic Codex workforce evidence"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [routing, codex, workforce, receipts, canary]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
supersedes: []
superseded_by: null
type: worklog
commit: 518ad6204e919270955a432c0387221b793a9ec5
short: 518ad62
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Restore atomic Codex workforce evidence

## Purpose

Restore the provider receipts, governed gap hiring, exact Codex activation
canary, and truthful specialist evidence that disappeared from native preflight
after its Store was removed to prevent partial writes.

## Approach

Workforce routing retains read access to the governed Store while its durable
routing and receipt writes are suppressed. Provider attempts and validated
contractor changes travel as bounded pending evidence. Pending specialists are
available through an in-memory roster and prompt view for staffing and
delegation construction. `mark_preflight_ready` commits the pending provider
receipts, hiring case, prompt version, worker, and routing decision inside the
same immediate transaction as the ready CAS; replay and CAS loss do not repeat
or leak those writes. Atomic preflight routes also do not publish in-memory
cache entries.

The Codex activation hook recognizes the current opaque persisted spawn message
only for the package-owned canary goal after its exact parent scope, task label,
and persisted assignment have already resolved. Ordinary goal mismatches remain
denied.

## Challenges encountered

The live Codex rollout persists the canary spawn message in opaque encrypted
form, while the former tests supplied plaintext. Atomic hiring also needed a
temporary exact-version prompt view so the contractor could be validated and
assigned before becoming durable. Review found and repaired daily-limit and
in-memory route-cache races at the ready boundary.

## Decisions and alternatives

[ADR-0112](../decisions/0112-stage-preflight-workforce-evidence-until-ready.md)
records the staged-evidence transaction boundary. Direct preflight writes and a
header-only repair were rejected because either could leave partial state or
claim evidence that did not exist.

## Verification

- 76 routing, receipt, dynamic-hiring, header, and activation-canary tests
  passed with warnings treated as errors.
- 29 preflight-bound tests passed with warnings treated as errors.
- 7 durable-continuation tests passed and 6 platform cases skipped.
- Ruff check and format verification passed across the production, test, and
  script trees.
- Metadata, policy availability, worklog-currentness, documentation, and
  whitespace validation passed.

## Follow-ups

Run the named fast production spine, merge the pull request, reinstall the exact
merge, and capture current installed Codex canary, specialist, delegation, and
model-receipt evidence under
[AR-199](../roadmap/issue-AR-199-restore-codex-workforce-evidence.md).
