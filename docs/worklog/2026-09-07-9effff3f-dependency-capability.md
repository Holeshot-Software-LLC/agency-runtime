---
title: "Reject ambiguous dependency-review JSON"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [security, ci, evidence, backlog]
related:
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
  - docs/roadmap/acceptance/evidence/AR-165-dependency-capability-20260907.md
  - docs/decisions/0228-reconcile-dependency-review-evidence-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 9effff3f6c4f4fbe59de8793df074a041e64dab9
short: 9effff3f
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md
---

# Worklog detail: Dependency capability JSON

## Approach and decision

Actual baseline executions reproduced duplicate-key error/identity overwrites
selecting fallback, plus object/non-finite success data reporting availability.
The reader now rejects duplicate keys, non-JSON constants, invalid UTF-8, excess
nesting and post-stat oversized reads with bounded diagnostics. HTTP 200 must
contain an array of objects. Both legitimate workflow paths, request bounds,
action pins, moderate threshold and aggregate remain unchanged. Do not restore
the optional permissions projection removed by 55a00db2.

ADR-0228 explicitly reconciles only old measurement/tracker criteria 8/9 before
review. Current identity is public/non-fork; exact API access is not hosted CI
or billing evidence. No savings claim is made, and AR-347's existing unmapped
legacy exemption applies. Original criteria are retained for provenance.

## Verification

Four baseline false classifications now reject without outputs. Twenty-five
new tests bring focused checks to 62 passes; full non-Windows workflow package
235 passes/five deselections; fresh named spine 1085 passes/three existing skips.
Ruff check/format 766 files, metadata and strict docs 1185 files, strict tracker
397 mapped/two historical PR exceptions, policy/worklog/diff checks all pass.
Same-byte DOM/browser receipts are reused explicitly; no exhaustive dispatch,
native Windows or attended host activation is claimed.

## Follow-ups

Freeze all nine builder rowsets at this candidate, require isolated verdicts,
and complete only if all satisfy. Publish one normal PR and merge before AR-166.
Hosted enforcement remains AR-159; the fresh requested Codex install still
reports unverified hook trust, activation required and mixed package projections.
