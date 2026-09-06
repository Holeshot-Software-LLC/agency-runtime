---
title: "Retire the superseded ZCode Stop checklist"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, zcode, supersession, evidence]
related:
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 5e2e5e66707a31040902ef0ec6f24d297c363d06
short: 5e2e5e66
date: 2026-09-05
pr: null
related_issues:
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
---

# Worklog: retire the superseded ZCode Stop checklist

## Purpose

Resolve the fifth oldest unfinished record without restoring superseded retry,
Agency-unavailable blocking or mandatory exhaustive-suite behavior.

## Approach

The actual shape fix is already implemented at both sites. ADR-0223 retires
AR-127 as superseded by AR-135, while ADR-0089 remains accepted. Preserve the
old checklist and history; current ZCode Stop/full-response proof remains
owned under AR-135. Do not treat the original preview-truncation hypothesis
as established diagnosis or claim a new live success.

## Challenges encountered

The wider host-hook/policy/turn-evidence package returns 133 passed and three
failures in 41.91s. These exact failures were already documented in August:
one expects removed public agency.delegate, two expect the old Codex/Claude
retry protocol. They remain recorded under the existing AR-176 fixture-cleanup
item; no test is hidden, skipped, rewritten or described as passing.

## Decisions and alternatives

ADR-0223 applies existing first-pass terminal, Rule-8 availability and bounded
verification authorities. Retiring the obsolete checklist is not acceptance of
its changed conditions. Restoring its obsolete conditions would regress the
current product; deleting the working wire-shape decision would be incorrect.

## Verification

- Current real-Store terminal/replay, ZCode unavailable/boundary, no-retry and
  completion-policy checks: 37 passed in 3.37s.
- Wider selected package: 133 pass/three known legacy failures, as above.
- Ruff check and format pass for 764 files; metadata/strict docs pass for 1121
  files before this detail; policy/worklog/diff pass. Tracker parity permits
  only AR-127's expected pending post-merge retirement closure.
- Runtime/tests/scripts/workflows and AR-119 matrix/vision are unchanged against
  79930464. Reuse this turn's named fast-spine/UI evidence; no exhaustive corpus,
  new live host trial, provider call, installation or Windows execution.

## Follow-ups

Merge, retire #151 as NOT_PLANNED, read back state/count, then review AR-129
while leaving Windows work with the owner. AR-135 owns current ZCode acceptance;
AR-176 owns the three already-known stale assertions.
