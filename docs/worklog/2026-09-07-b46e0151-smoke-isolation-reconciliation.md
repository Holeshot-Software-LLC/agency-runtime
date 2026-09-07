---
title: "Reconcile AR-181 smoke isolation and Linux proof"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, smoke, isolation]
related:
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
  - docs/roadmap/acceptance/evidence/AR-181-smoke-reconciliation-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: b46e015193b11e2ab4b62faa77e5e064506a247a
short: b46e0151
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/731
related_issues:
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
---

# Worklog detail: Reconcile AR-181 smoke isolation and Linux proof

## Purpose

Distinguish already implemented Linux smoke performance from the remaining
native Windows timing requirement.

## Approach

Record37 focused passes/two deselections, the actual existing-install8/0/0
smoke in4.25s, and separate AR407 exact-wheel8/0/0 in5.09s. Preserve timing
and artifact identity rather than combining distinct runs.

## Challenges encountered

Original criterion2 demanded a separate home per host, contradicting even the
original parent implementation. Both original and current smoke share one
explicit private invocation home with distinct host bundle paths.

## Decisions and alternatives

Explicitly correct criterion2 to existing ADR0026; preserve its original words
in the receipt. No new architecture or permission boundary, no verifier verdict
and no false Windows qualification. Do not rerun completed Linux checks solely
for paperwork.

## Verification

Recorded source, installed execution and typed-failure diagnostic evidence.
Metadata, policy, worklog, docs, strict tracker, Ruff and diff publication
checks. No runtime change, model invocation or exhaustive gate.

## Follow-ups

AR181 remains in_progress. Owner supplies native Windows exact-wheel timing;
continue AR183/184 Linux producer proof next.

Substantive `b46e0151` corrects the contradictory isolation wording under existing ADR0026 and retains the Windows hold; no acceptance verdict is manufactured.

Filing `f0486afa` records actual live five-call critic starvation misclassification and dropped effective timeouts as AR408/#732, keeping tracker parity while the independent repair is reviewed. No call-budget policy changes or runtime code are included in this filing.
