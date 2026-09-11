---
title: "AR-439 acceptance verification record"
status: active
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [acceptance, workforce, planner, staffing-verifier]
related:
  - docs/roadmap/issue-AR-439-planner-method-capabilities-force-incoherent-coverage.md
  - docs/decisions/0252-bind-mandatory-capabilities-to-the-unit-shape.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-439
candidate_commit: 003d31e608614785b6b2f6c402bd5942250ec0ad
evidence_cutoff: 2026-09-11
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/875
---

# AR-439 acceptance verification record

## Builder evidence

The builder cites observations and does not judge. Scope is the split
between mandatory and advisory capabilities in the staffing verifier
(ADR-0252), the advisory row on the applied planner attempt, and one fresh
native run per host on the exact ordinary-review wording after the PR #879
reinstall. Live observations are single samples; the planner and recruiter
are stochastic; codex is excluded because it is activation-required after
the reinstall. The first merged form (PR #876) left `risk-analysis`
mandatory and one host was still rejected on the capability axis; the
follow-up (PR #879) moved it into the shape vocabulary, and the measurement
cited under criterion 3 is the one taken after that follow-up.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | The shape vocabulary: the twelve authority-and-lifecycle rules plus the architecture and risk-analysis readings | 2026-09-11 | agency_runtime/core/workforce/staffing_verifier.py:311-328 |
| 1 | file | `mandatory_capabilities` keeps the owned capability, non-shape specialties and novelties; `advisory_capabilities` names the rest | 2026-09-11 | agency_runtime/core/workforce/staffing_verifier.py:353-380 |
| 1 | file | `_requirements` derives its capability tokens from the mandatory set only | 2026-09-11 | agency_runtime/core/workforce/staffing_verifier.py:532-542 |
| 1 | test | Vocabulary pinned; the observed shapes (`implementation` on a review, `analysis` on test-code, `coordination` on a merge, `planning` on an analysis, `risk-analysis` on a review) are advisory while specialties and a novelty stay mandatory; the unit keeps every planner-named capability; a lone reviewer covers a review that named `implementation`; an undeclared specialty is still a hiring gap | 2026-09-11 | tests/test_capability_shape_coherence.py:103-241 |
| 1 | test | The compiler keeps every planner-named capability and its older drops still hold | 2026-09-11 | tests/test_capability_shape_coherence.py:243-262 |
| 1 | command-output | Focused regressions pass, including the AR-391 derivation account on `threat-modeling` | 2026-09-11 | docs/roadmap/evidence/AR-439-focused-tests-20260911.txt:1-41 |
| 2 | file | Advisory wire prefix, closed code, three-key row, bounds and identifier charset | 2026-09-11 | agency_runtime/core/selector/receipt_projection.py:103-115 |
| 2 | file | Detail dispatcher routes the advisory prefix; row and detail projection refuse a malformed detail whole | 2026-09-11 | agency_runtime/core/selector/receipt_projection.py:490-538 |
| 2 | file | `_advisory_capability_detail` writes one row per unit from the parsed plan | 2026-09-11 | agency_runtime/core/workforce/inference.py:4730-4748 |
| 2 | file | The planner stage attaches the detail to the applied planner attempt only when a planner call was spent | 2026-09-11 | agency_runtime/core/workforce/inference.py:5249-5264 |
| 2 | test | End-to-end: the advisory row rides the applied planner attempt into the routing receipt and the preflight-failure receipt, survives re-projection; malformed wire forms project blank; the row is exactly its three keys; the planner prompt names what is mandatory | 2026-09-11 | tests/test_capability_shape_coherence.py:276-397 |
| 2 | command-output | Named fast spine passes on the follow-up tip | 2026-09-11 | docs/roadmap/evidence/AR-439-fast-spine-20260911.txt:18-18 |
| 2 | command-output | Decision conformance kills all 188 mutations on the follow-up tip | 2026-09-11 | docs/roadmap/evidence/AR-439-decision-conformance-20260911.json:1-13 |
| 3 | file | Runtime under test after the follow-up reinstall: main `f900ee3e`, digest `afb7790bd7a2` | 2026-09-11 | docs/roadmap/evidence/AR-439-live-measurement-20260911.json:6-11 |
| 3 | file | Four runs (claude, hermes, zcode, openclaw): every planner attempt carries `plan_capability_advisory` rows, `capability_axis_rejections` 0 on each, three staffed with two units, claude a critic veto | 2026-09-11 | docs/roadmap/evidence/AR-439-live-measurement-20260911.json:12-374 |
| 3 | file | Critic packets, the store-wide count of `staff_without_safe_team` rows since the install (0), the 17-row baseline reference and the findings | 2026-09-11 | docs/roadmap/evidence/AR-439-live-measurement-20260911.json:375-426 |
| 3 | file | The intermediate digest's measurement and the in-process diagnostic that named `risk-analysis` as the remaining forcing capability | 2026-09-11 | docs/roadmap/evidence/AR-439-post-merge-measurement-20260911.json:316-421 |
| 3 | receipt | hermes run, preflight ready, two advisory rows, two units | 2026-09-11 | 18304f85-9579-4b30-80f7-e06563733a87 |
| 3 | receipt | openclaw run, preflight ready, one advisory row, two units, no recruiter rejection | 2026-09-11 | fc2c6d19-e3bb-4581-b715-b051a5852031 |
| 3 | tracker | Tracker issue for parity | 2026-09-11 | https://github.com/Holeshot-Software-LLC/agency-runtime/issues/875 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-439.1-20260911-d2949948` | `1450a9003d25723999392683ce5b1f050aa99240ed84c983219d3ce52b444336` | 2026-09-11 | staffing_verifier.py:353-378 and _requirements:532-540 make only the owned capability plus non-shape specialties typed requirements; test_capability_shape_coherence.py:103-256 pins the four shapes, lone-reviewer coverage, specialty gap and compiler drops, all PASSED in the AR-439 log. |
| 3 | satisfied | `AR-439.3-20260911-fe013201` | `b0a321d8ef9654916992fabb4643354f6fb308bbdda7f0e09cdb02df49c72795` | 2026-09-11 | AR-439-live-measurement JSON lines 12-374 show four post-reinstall runs on one wording, each with plan_capability_advisory rows and capability_axis_rejections 0; line 416 gives store-wide staff_without_safe_team 0, line 418 the 17-row baseline; claude's sole failure was an off-axis critic veto. |
| 2 | satisfied | `AR-439.2-20260911-d4d3b98d` | `6f639334f088b8caf6e589817baec63d41a0e39e7d97656d9bf362da714b5827` | 2026-09-11 | receipt_projection.py:336-537 routes the prefix and blanks malformed details whole; inference.py:5249-5261 attaches it to the applied planner attempt; tests 276-399 assert the closed 3-key row on both receipts; focused (40), fast-spine (1152) and 188/188 conformance evidence pass. |
