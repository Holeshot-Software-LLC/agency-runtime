---
title: "AR-235 active recovery capsule"
status: active
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [handoff, workforce, hiring, security, routing, recovery]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/roadmap/issue-AR-238-isolated-security-review-with-bounded-repair.md
  - docs/roadmap/issue-AR-240-amend-first-staffing-default.md
  - docs/roadmap/issue-AR-241-cap-removal-and-dashboard-visibility.md
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-235
branch: ar-243-workforce-promotion-readiness-parity
evidence_commit: b4f7a2b84cb69aa2ad404258ab4e59a4731625f9
minimum_ledger_commit: b4f7a2b84cb69aa2ad404258ab4e59a4731625f9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/244
---

# AR-235 active recovery capsule

All six AR-235 slices are implemented and locally committed. The branches
are stacked: ar-238 → ar-240 → ar-241 → ar-242 → ar-243. None are pushed or
merged to main yet (pending operator authorization).

## checkpoint

- All six slices pass the focused test spine
  (test_workforce_dynamic_hiring, test_workforce_hiring_contract,
  test_workforce_selection_safety, test_workforce_promotion,
  test_routing_correctness, test_decision_conformance) with -W error.
- The stacked branches are not on main or origin. They need to be
  squashed/merged into main as a group or individually PR'd.

## completed-evidence

- Slice 1 (inference profiles, ADR-0153): commit `66a066f` on main.
- Slice 2-3 (security review + bounded repair, AR-238): commits
  `a331630`, `b5bd549`, `c9bc13e` on branch ar-238-isolated-security-review.
  New `_security_review` isolated stage, `_safety_repair_loop` bounded by
  `hiring_repair_budget: 3`, marker classes as reviewer hints, reviewer is
  the gate (human_approval_required=False on gap-hire path).
- Slice 4 (amend-first, AR-240): commits `0b6c059`, `ee2f727` on branch
  ar-240. `allow_existing_worker_amendment` default True,
  `amend_overlap_threshold: 0.7` gate, below-threshold fallthrough to hire.
- Slice 5 (cap removal, AR-241): commits `e750593`, `e5d4eb3`,
  `6b6b505`, `e79025d` on branch ar-241. Hard caps removed;
  `max_hires_per_turn: 16`, `daily_hire_alert_threshold: 50` soft bounds;
  daily count in critic_evidence; decision-conformance anchor updated.
- Slice 6 (auto-promotion, AR-242): commits `f85074f`, `8adcc69` on branch
  ar-242. `auto_promote_successes: 3`, `contractor_review_days: 7`,
  review-window suppression in promotion_readiness.

## exact-blocker

- Branches need merge to main + push + tracker issue creation — all
  outward actions pending operator authorization.
- AR-235 acceptance item 7 (dashboard operator review plane: per-contractor
  activity log, per-case security review trail, workforce health summary)
  is NOT done. It is dashboard-side work that belongs to the AR-236 parity
  umbrella, not a separate AR-235 slice. The data is available; the views
  are not built.

## same-task-continuity

Continue merging the stacked branches to main when authorized. The AR-236
sub-issues (S3-S10) are dashboard-side parity work that can proceed
independently.

## next-bounded-work-package

1. Merge ar-238 → ar-240 → ar-241 → ar-242 → ar-243 into main (or rebase
   each onto main and PR individually).
2. Push to origin + create tracker issues for AR-238/240/241/242/243.
3. Continue AR-236 sub-issues S3-S10 (dashboard-side parity).

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/verify_docs.py
python scripts/update_worklog.py --check
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_dynamic_hiring.py \
  tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py \
  tests/test_workforce_promotion.py tests/test_routing_correctness.py \
  tests/test_decision_conformance.py tests/test_dashboard.py \
  tests/test_workforce_cli.py -q -W error
git diff --check
~~~

## constraints

- No push, PR, tracker mutation without authorization.
- Keep AR-235 open until the dashboard operator-review-plane acceptance
  item has current evidence (either via an AR-236 sub-issue or standalone).
