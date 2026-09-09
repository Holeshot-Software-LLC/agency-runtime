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
candidate_commit: c32dd73234255855f891f6b759eeba8516ef9aaa
evidence_cutoff: 2026-09-09
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/820
---

# AR-425 acceptance verification record

## Builder evidence

The builder cites evidence and does not judge criteria. Failed native turns remain
failed; this packet does not establish AR-404 all-host reliability.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 2 | file | Same unit, context or independence class cannot assure its own modifying work; missing independent assurance is rejected | 2026-09-09 | agency_runtime/core/workforce/staffing_verifier.py:1030-1083 |
| 2 | file | Provider call rejects exhausted budget or reserved required slots before invoker | 2026-09-09 | agency_runtime/core/workforce/inference.py:1762-1781 |
| 2 | file | Budget consume refuses used maximum and remaining never becomes negative | 2026-09-09 | agency_runtime/core/workforce/inference.py:1222-1240 |
| 2 | file | Actual fast-mode test composes planner and recruiter repairs with exactly four calls, then no extra response | 2026-09-09 | tests/test_workforce_inference.py:2362-2395 |
| 2 | file | Actual planner repair rejects missing security/evidence assurance and wrong order; repaired graph is inference's returned graph | 2026-09-09 | tests/test_workforce_inference.py:2261-2331 |
| 4 | command-output | Exact compact check counts, source identity, native planner repair then critic approval and accepted hash, with limitations | 2026-09-09 | docs/roadmap/evidence/AR-425-bounded-verification-summary-20260909.json:1-51 |
| 2 | file | Rejected model data enters only the bounded planner repair field | 2026-09-09 | agency_runtime/core/workforce/inference.py:1701-1716 |
| 2 | file | Every replacement goes back through parser before accepted; same two-attempt loop | 2026-09-09 | agency_runtime/core/workforce/inference.py:1950-1995 |
| 1 | command-output | Old source real-orchestration regression raises KeyError for missing rejected_plan_untrusted; known-code regression also fails | 2026-09-09 | docs/roadmap/evidence/AR-425-validation-20260909.json:1-162 |
| 1 | file | Real plan_and_staff_workforce regression sends rejected object through one repair and observes parser validation | 2026-09-09 | tests/test_workforce_inference.py:1936-1980 |
| 2 | file | Hostile answer is data, oversized answer omitted, nonplanner excludes field | 2026-09-09 | tests/test_planner_repair_context.py:1-89 |
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
| 1 | satisfied | `AR-425.1-20260909-8862f6fa` | `faac3cac9863db004ec993db9fff8b99ecd8086bc40beaa55b47c1db6de1e8fb` | 2026-09-09 | tests/test_workforce_inference.py:1936-1980 exercises plan_and_staff_workforce and asserts rejected-plan context in the repair prompt; AR-425-validation-20260909.json records the original orchestration failure as KeyError rejected_plan_untrusted. |
| 2 | satisfied | `AR-425.2-20260909-d5fb19d3` | `fda5185f6ba7508c8d6bcf1b9ad67dc9a2d2f7e57cbe6b85cd001a075206e422` | 2026-09-09 | inference.py bounds planner-only untrusted repair data, records rejection, reparses replacements and enforces call budgets; staffing_verifier.py enforces independent assurance, with supporting repair and four-call tests. |
| 3 | satisfied | `AR-425.3-20260909-e006aacb` | `fc084e7b4cd186e31096a82fa624f6e677f43e4f0e40b9c5ef5c2e34707bb72c` | 2026-09-09 | plan_policy.py:338-357 maps exact known failures to closed codes and unknown errors to a generic code; test_planner_repair_context.py:1-89 verifies terminal projection preserves those codes without validation details or rejected content. |
| 4 | satisfied | `AR-425.4-20260909-1c0fa05a` | `db322ab78f96dea54121cfd0d0c516de477ebc3972ef5506de4eea6aa62ff05d` | 2026-09-09 | AR-425 validation and bounded-verification summary record passing checks; the planner diagnostic and AR-404 native traces preserve rejected attempts, accepted outcomes, and explicit replay, causality, and unknown-error limitations. |
