---
title: "AR-240: Amend-first staffing default (slice 4 of AR-235)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [workforce, hiring, staffing, sub-issue]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-238-isolated-security-review-with-bounded-repair.md
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/config_defaults.yaml
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-240
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/249"
depends_on: []
blocks: []
---

# AR-240: Amend-first staffing default (slice 4 of AR-235)

## Problem

AR-235 §4 inverts the `allow_existing_worker_amendment` default from
`False` to `True`. Today the default forces every gap to spawn a new
contractor; near-matches that would be cheap and safe to amend are
rejected as "stretch a near-match into a generalist." The result is
workforce duplication for scenarios that differ only in narrow scope.

## Current state

- `allow_existing_worker_amendment: bool = False` in
  `hire_contractor_for_gap` (`hiring.py`). When the recruiter returns
  `action: "amend"` and the flag is False, `_validated_candidate`
  rejects with `task_gap_requires_distinct_specialist`.
- The recruiter's `duplicate_evidence` block already returns
  `decision: {"enum": ["hire", "reuse", "amend"]}` with a
  `coherent_amendment_target` slug and a `maximum_overlap` (0-1) score.
- The amendment agent `_amendment_agent` (`hiring.py`) is implemented
  and produces a byte-preserving additive amendment. Only the gating
  default is conservative.
- The `_HIRE_SYSTEM` prompt says "Do not stretch or amend a near-match
  to fill an ordinary task gap" — the opposite of amend-first.

## Approach

1. Flip the default of `allow_existing_worker_amendment` from `False`
   to `True` in `hire_contractor_for_gap`.
2. Add `amend_overlap_threshold: 0.7` config knob. When the recruiter
   returns `action: "amend"` with `maximum_overlap >= threshold`, the
   `_amendment_agent` runs. Below threshold or with no coherent target,
   fall through to the standard hire path.
3. Update the `_HIRE_SYSTEM` prompt to reflect the amend-first policy:
   prefer amend with a coherent target; only stretch when no coherent
   target exists.

## Dependencies

- AR-235 slices 1-3 — done (inference profiles, security review).

## Acceptance

- [ ] `allow_existing_worker_amendment` defaults to `True`.
- [ ] `amend_overlap_threshold: 0.7` config knob is added and wired.
- [ ] When the recruiter returns `action: "amend"` with
      `coherent_amendment_target` and `maximum_overlap >= threshold`,
      the `_amendment_agent` runs. Below threshold or with no coherent
      target, the standard hire path runs.
- [ ] The `_HIRE_SYSTEM` prompt reflects the amend-first policy.
- [ ] Focused tests cover: amend-first default, below-threshold
      fallthrough, reuse unchanged.
