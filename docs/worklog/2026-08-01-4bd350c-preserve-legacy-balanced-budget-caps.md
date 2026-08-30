---
title: "Worklog detail: Preserve legacy balanced budget caps"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [configuration, workforce, compatibility, budgets, review]
related:
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
supersedes: []
superseded_by: null
type: worklog
commit: 4bd350c
short: 4bd350c
date: 2026-08-01
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/220
related_issues:
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
---

# Worklog detail: Preserve legacy balanced budget caps

## Purpose

Address exact-head Codex review finding `discussion_r3694929406`. Raising the
fresh fast default to four made a previously valid partial configuration with
only `balanced_call_budget: 3` fail validation against an omitted fast value.

## Approach

Partial validation now bounds the omitted fast value to an explicit balanced
cap. Runtime default merging applies the same compatibility rule while leaving
the persisted partial document unchanged. An explicit fast value still wins,
fresh configurations still default to four, and the ordering validator still
rejects an explicit fast value above balanced.

## Challenges encountered

Changing validation alone would have admitted the document but produced an
incoherent effective snapshot after bundled-default merging. The repair binds
both boundaries to the same operator-owned cap.

## Decisions and alternatives

Persisting a synthetic fast value during load was rejected because a read must
not rewrite user configuration. Dropping tier ordering for all partial documents
was rejected because explicit incoherent updates must still fail.

## Verification

- Exact legacy partial-config regression plus adjacent default, explicit
  override, and incoherent-update checks: 8 passed.
- Named Python production spine: 643 passed, 6 skipped.
- Dashboard UI: 110 passed; routing evaluation: 39/39 gates passed.
- Decision conformance: baseline passed, 73/73 mutations killed, zero survived
  or invalid, the target budget mutation was killed, and
  `source_unchanged=true`.
- Repository-wide Ruff lint/format, documentation validation, and
  `git diff --check` pass.

## Follow-ups

Run the named gate on the repaired head, push, resolve the exact review thread,
and obtain a clean exact-head Codex review before merge.
