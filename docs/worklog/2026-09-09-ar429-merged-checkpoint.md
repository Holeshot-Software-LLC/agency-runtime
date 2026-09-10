---
title: "Checkpoint merged AR-429 and remaining priority host gates"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [handoff, reliability, hermes]
related:
  - docs/roadmap/issue-AR-429-ground-recruiter-specialties-in-unit-scope.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-429-ground-recruiter-specialties-in-unit-scope.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Checkpoint merged AR-429 and remaining priority host gates

## Purpose

PR836 merged at82090e11 and closed AR-429/#834 after exact native and isolated
acceptance. Replace pre-merge recovery instructions with current state.

## Approach

The capsule separates recipe21 Hermes proof, prior Claude/Codex/OpenClaw evidence,
AR-418 upstream adoption and historical invalid receipts. It names the exact
remaining Hermes review/assurance receipt so the next package starts from evidence.

## Challenges encountered

Two optional foundation failures also reproduce on main and remain deferred in
AR-430. The long-lived Codex parent remains stale; a reinstall is not a restart.

## Decisions and alternatives

No source or staffing authority change. Preserve the owner order and Zcode
implementation deferral, while keeping all five hosts in the umbrella scope.

## Verification

Source/tests unchanged from validated artifact47241e5e. Prior fast/native and
isolated results remain exact; metadata, docs, worklog and tracker checks cover
this record-only checkpoint. No exhaustive or Windows workflow ran.

## Follow-ups

Inspect Hermes review trace20260909_113727_2e00b0:6c87a1d6-a92a-493a-9f11-7c1b27e84a58:e03a9447
under AR-404. AR-418 retains truncation adoption/cap proof; AR-430 owns deferred
foundation test maintenance. No failed receipt may be reopened or manually accepted.
