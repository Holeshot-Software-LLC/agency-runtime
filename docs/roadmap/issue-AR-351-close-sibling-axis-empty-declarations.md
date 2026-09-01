---
title: "AR-351: Explicit-empty sibling axes still grant coverage or silently never match"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, staffing, validation, hardening]
related:
  - docs/roadmap/issue-AR-343-reject-explicit-empty-artifact-kinds.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-351
priority: p3
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/409
depends_on: []
blocks: []
---

# AR-351: Explicit-empty sibling axes still grant coverage or silently never match

## Problem

AR-343 closed the explicit-empty hole for `artifact_kinds` only. The
same defect class survives on the sibling axes (found by the PR #401
review): an explicit `stacks: []` collapses to omission at projection
and lands in `_coverage`'s per-axis stack wildcard
(`agency_runtime/core/workforce/staffing_verifier.py:435-446`), so a
positive "owns no stacks" declaration proves stack coverage for every
unit language and framework; explicit-empty `lifecycle_phases` or
`domains` project to `()` and silently never match any unit, making the
specialist unstaffable on those axes — the exact "silently never match"
failure AR-343's own rationale says must be rejected.

## Current state

No shipped producer emits these shapes today (the same reachability
posture AR-343 had); this is validation hardening. The wildcard-branch
semantics for hand-built contracts are pinned by
`test_wildcard_coverage_is_reserved_for_truly_untyped_contracts`.

## Approach

Mirror the AR-343 rule on each axis at projection: reject an explicitly
empty declaration (omission still derives), decide per axis whether an
all-unknown set is rejectable, and keep `parse_workforce_contract`'s
legacy tolerance so stored rows re-derive instead of failing roster
reads.

## Dependencies

- AR-343's shipped validation shape (this PR) as the pattern to mirror.

## Acceptance

- [ ] Explicitly empty `stacks`, `lifecycle_phases`, and `domains`
      declarations are rejected at projection (omission still derives).
- [ ] Stored legacy rows with those shapes remain parseable via
      re-derivation.
- [ ] Regression tests cover projection rejection, parse tolerance, and
      the stack-wildcard boundary in `staffing_verifier`.
