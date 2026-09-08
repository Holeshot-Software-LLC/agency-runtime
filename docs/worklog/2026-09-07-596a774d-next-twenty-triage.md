---
title: "Triage the next twenty unfinished backlog records"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, evidence]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-next20-triage-20260907.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 596a774d7a087b520ce912a90937484e8d4ad30a
short: 596a774d
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/748
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog detail: docs(backlog): triage next twenty unfinished records

## Purpose

Separate actual remaining code from obsolete checklists and missing proof in
the next twenty unfinished, non-Windows-only canonical records.

## Approach

Inspect canonical chronology, existing runtime call sites, and governing
decisions at `cbba0fd9` plus its faithful ledger `887c8712`. Preserve every
canonical status and literal criterion. Record one bounded twenty-row audit,
not twenty independent reviews or acceptance judgments.

## Challenges encountered

Several records combine completed implementation with later evidence holds,
and older requirements contradict current owner authority, the resident steward,
or inference budgets. AR-250 explicitly defers its only unfinished UI feature.

## Decisions and alternatives

Recommend the existing AR-270 closed OpenClaw provenance repair and AR-251
plain-card extension as concrete implementation candidates. Do not restore
removed grants, Windows presence helpers, an imported resident pair, or old
three-call defaults. Broader parity remains an umbrella, not another defect.

## Verification

Read-only source/document inspection; metadata check passed for 1268 Markdown
documents before this detail was added. `git diff --check` passed. No tests,
CI, native calls, model requests, installed-state changes, or tracker writes
ran for this package. Owner requested code-first work and deferred tests/CI.

## Follow-ups

The final delivery owner added the reciprocal AR-404 links and included this
report in PR #748. AR-251 and AR-270 implementation remain separately scoped;
every other record keeps its explicit proof or policy-reconciliation obligation.
