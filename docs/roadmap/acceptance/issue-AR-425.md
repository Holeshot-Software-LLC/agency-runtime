---
title: "AR-425 acceptance verification record"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [acceptance, native, reliability]
related:
  - docs/roadmap/issue-AR-425-preserve-planner-repair-context.md
  - docs/worklog/2026-09-09-planner-repair-context.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-425
candidate_commit: 115b471f1f32a369fea1cf8dc9fd1d7118e9e679
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/820
---

# AR-425 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge criteria. Failed native turns remain
failed; this packet does not establish AR-404 all-host reliability.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 4 | command-output | Exact compact check counts, source identity, native planner repair then critic approval and accepted hash, with limitations | 2026-09-09 | docs/roadmap/evidence/AR-425-bounded-verification-summary-20260909.json:1-65 |
| 2 | file | Rejected model data enters only the bounded planner repair field | 2026-09-09 | agency_runtime/core/workforce/inference.py:1701-1716 |
| 2 | file | Every replacement goes back through parser before accepted; same two-attempt loop | 2026-09-09 | agency_runtime/core/workforce/inference.py:1950-1995 |
| 2 | file | Rejected content has no worker or approval authority | 2026-09-09 | agency_runtime/core/workforce/intent.py:368-387 |
| 1 | command-output | Old source real-orchestration regression raises KeyError for missing rejected_plan_untrusted; known-code regression also fails | 2026-09-09 | docs/roadmap/evidence/AR-425-validation-20260909.json:1-162 |
| 1 | file | Real plan_and_staff_workforce regression sends rejected object through one repair and observes parser validation | 2026-09-09 | tests/test_workforce_inference.py:1936-1980 |
| 2 | file | Existing stage forwards rejected result into bounded planner-only repair data; replacement traverses same parser and call loop | 2026-09-09 | agency_runtime/core/workforce/inference.py:1809-1839 |
| 2 | file | Hostile answer is data, oversized answer omitted, nonplanner excludes field | 2026-09-09 | tests/test_planner_repair_context.py:1-89 |
| 2 | file | Work-unit cap, assurance graph and per-stage budget tests retain rejection and inference authority | 2026-09-09 | tests/test_workforce_inference.py:2031-2077 |
| 2 | file | Critic remains veto-only for already verified teams and bounded fallback preserves critic requirement | 2026-09-09 | tests/test_workforce_inference.py:3146-3210 |
| 3 | file | Exact runtime errors map to five known codes; unknown and suffix-injected text remain generic | 2026-09-09 | agency_runtime/core/workforce/plan_policy.py:338-357 |
| 3 | file | Closed codes survive terminal projection without validation_detail or rejected content | 2026-09-09 | tests/test_planner_repair_context.py:1-89 |
| 4 | command-output | Focused143, production1151/3skipped, UI224 and docs/tracker/Ruff checks | 2026-09-09 | docs/roadmap/evidence/AR-425-validation-20260909.json:1-162 |
| 4 | command-output | Frozen source188/188 killed, zero invalid/survivors; first setup failure preserved separately | 2026-09-09 | docs/roadmap/evidence/AR-425-conformance-20260909.json:1-2626 |
| 4 | file | Baseline new planner-only diagnostic missing correctness review followed by accepted repair; not exact old native replay | 2026-09-09 | docs/roadmap/evidence/AR-425-planner-diagnostic-20260909.json:1-360 |
| 4 | file | Candidate native planner rejects first response, accepts one repair, independent critic accepts; fourcards, truthfulheaders and accepted final response | 2026-09-09 | docs/roadmap/evidence/AR-404-claude-large-context-after-planner-context-20260909.json:1-540 |
| 4 | file | Original native two-rejection failure retained; second semantic cause remains unknown | 2026-09-09 | docs/roadmap/evidence/AR-404-claude-suite-after-tool-permission-20260909.json:1-176 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
