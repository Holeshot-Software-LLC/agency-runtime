---
title: "Worklog: Govern bounded hiring evidence delivery"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [dashboard, workforce, availability, pagination]
related:
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
supersedes: []
superseded_by: null
type: worklog
commit: e62230c9560709a5e3161592c0d039498a353cd5
short: e62230c
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
---

# Worklog: Govern bounded hiring evidence delivery

## Purpose

Record the independently reproduced dashboard availability defect before
implementation: one legal hiring collection page can materialize hundreds of
MiB and the browser can eagerly retain many such pages.

## Approach

Create AR-155 under the existing complete-collection decision. The issue
separates fixed-field collection summaries from the existing exact-case API,
which remains authoritative for complete evidence on explicit inspection.

## Challenges encountered

Row-count bounds alone looked safe until the five independent 256 KiB evidence
documents were multiplied by the 200-row server page and 100-page browser cap.
The threat is ordinary accumulated data, so loopback binding and authentication
do not prevent the availability failure.

## Decisions and alternatives

Do not raise limits, silently truncate evidence, or weaken exact-case fidelity.
Keep full documents behind an on-demand exact lookup and make collection payload
size a tested contract under ADR-0095.

## Verification

- Documentation metadata: 394 maintained Markdown files passed.
- Documentation integrity: 394 maintained Markdown files passed.
- Diff whitespace validation: passed.

## Follow-ups

Implement and verify AR-155 before final artifact and browser QA.
