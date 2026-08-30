---
title: "Worklog: Remove dead private inference paths"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [maintenance, workforce, dead-code, inference]
related:
  - docs/roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md
supersedes: []
superseded_by: null
type: worklog
commit: a1efe31acc61b4e7ab6068fe3736b94247ef8e6c
short: a1efe31
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md
---

# Worklog: Remove dead private inference paths

## Purpose

Remove an independently proven unreachable compatibility island from the
workforce inference module without changing the live compact planner,
recruiter, critic, deterministic floor, schemas, or exports.

## Approach

A repository-wide exact-name and dynamic-entrypoint audit first proved seven
private helpers and their closed dependency chain reachable only from their
definitions and private tests. The change removes 590 production lines while
adding one replacement line, then ports remaining shortlist fixtures to
canonical public plan documents before deleting tests that asserted only the
dead internals.

## Challenges encountered

The live recruiter payload still contains a field named `detail_cards`, but it
does not call the removed `_detail_cards` helper. Exact reachability and
export checks kept that public payload contract distinct from the dead helper.

## Decisions and alternatives

No broad mechanical rewrite was combined with this change. Large live
functions and remaining helper consolidation stay separately reviewable under
AR-141, while compatibility wrappers and public schemas remain intact.

## Verification

- Owning inference and selection-safety suite: 52 passed, 1 skipped, and 1
  expected failure.
- Repository-wide production/export/dynamic-entrypoint search: no removed name
  is reachable.
- Ruff check, format check, documentation validation, and diff check: passed.

## Follow-ups

AR-141 remains open for separately reviewed JSON/helper consolidation and
large-function decomposition.
