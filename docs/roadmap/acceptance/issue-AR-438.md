---
title: "AR-438 acceptance verification record"
status: active
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [acceptance, workforce, planner, plan-policy]
related:
  - docs/roadmap/issue-AR-438-cap-ordinary-asks-at-two-units.md
  - docs/decisions/0251-cap-ordinary-asks-at-two-planned-units.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-438
candidate_commit: 5a5d0ffa7250282d6b8b4e8e9cfa82af3521d400
evidence_cutoff: 2026-09-11
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/867
---

# AR-438 acceptance verification record

## Builder evidence

The builder cites observations and does not judge. Scope is the two-unit
planning ceiling for ordinary asks (ADR-0251), its route wiring, and one
fresh native run per installed host on the exact ordinary-review wording
after the PR #869 reinstall. Each live observation is a single sample; the
planner and recruiter are stochastic and no controlled A/B was run. Codex is
excluded from the live batch because it is activation-required pending the
owner trust screen. The applied ceiling reaches no receipt field; the
observable is the planned unit count on each run's routing receipt.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Ceiling constant, broad change-verb vocabulary and `planning_unit_ceiling` returning None for shape-expanding or change-verb-beside-code-noun asks and 2 otherwise | 2026-09-11 | agency_runtime/core/workforce/plan_policy.py:752-799 |
| 1 | file | Shared `RequestProfile` classification reused by `plan_policy_violations` and the ceiling | 2026-09-11 | agency_runtime/core/workforce/plan_policy.py:687-750 |
| 1 | test | Ordinary review, merge, handoff, README and install wordings return 2; code-mutation, security-review, repository-mapping and regulated-assurance wordings return None; negated scope and the change-verb guard | 2026-09-11 | tests/test_ordinary_ask_unit_ceiling.py:28-71 |
| 1 | command-output | Focused ceiling and documentation regressions pass | 2026-09-11 | docs/roadmap/evidence/AR-438-focused-tests-20260911.txt:1-44 |
| 2 | file | `_workforce_planning_options` returns the canary and inquiry one-unit contracts first and the ordinary ceiling as `max_planned_units` otherwise | 2026-09-11 | agency_runtime/core/selector/pipeline.py:1179-1209 |
| 2 | file | Route call site passes the request text into the planning options | 2026-09-11 | agency_runtime/core/selector/pipeline.py:2184-2188 |
| 2 | test | Planning options apply the ceiling only to ordinary asks and the route passes the request text | 2026-09-11 | tests/test_ordinary_ask_unit_ceiling.py:73-108 |
| 2 | test | Ordinary canary-text route without the restricted environment carries `max_planned_units` 2 and no artifact contract | 2026-09-11 | tests/test_activation_canary_contract.py:596-603 |
| 2 | test | Activation-canary route still carries its one-unit contract | 2026-09-11 | tests/test_activation_canary_contract.py:283-283 |
| 2 | command-output | Named fast spine passes on the branch tip | 2026-09-11 | docs/roadmap/evidence/AR-438-fast-spine-20260911.txt:18-18 |
| 2 | command-output | Decision conformance kills all 188 mutations on the branch tip | 2026-09-11 | docs/roadmap/evidence/AR-438-decision-conformance-20260911.json:1-13 |
| 3 | file | Runtime under test: main `1e1ca41c`, digest `98f5ddda00ce`, five hosts installed | 2026-09-11 | docs/roadmap/evidence/AR-438-four-host-measurement-20260911.json:6-17 |
| 3 | file | Four ordinary-review runs (claude, hermes, zcode, openclaw) each with `planned_units` 2, `staffing_status` accepted and every provider attempt listed | 2026-09-11 | docs/roadmap/evidence/AR-438-four-host-measurement-20260911.json:38-273 |
| 3 | file | Four captured critic packets, each `approved` true with empty reason codes | 2026-09-11 | docs/roadmap/evidence/AR-438-four-host-measurement-20260911.json:274-318 |
| 3 | file | Change-verb wording planned 3 units and no-code-noun wording planned 2, both approved | 2026-09-11 | docs/roadmap/evidence/AR-438-four-host-measurement-20260911.json:319-475 |
| 3 | file | Pre-change batch of 2026-09-11 on the same wording: 1 of 4 staffed | 2026-09-11 | docs/roadmap/evidence/AR-438-four-host-measurement-20260911.json:476-599 |
| 3 | receipt | claude run, preflight ready, two units (hermes df976d21 and openclaw bda59c0d are cited in the evidence file) | 2026-09-11 | 12e2d468-b876-401c-bcb2-48a577c2a63f |
| 3 | receipt | zcode run, preflight ready, two units after three recruiter attempts | 2026-09-11 | 56fe8142-17f7-454b-b028-31074a2ac1e9 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-438.1-20260911-4b58418c` | `af69332bfaa9adb79b30d7a15f7640a1be5e841d997d658c795d4ad53d128df4` | 2026-09-11 | Traced planning_unit_ceiling (plan_policy.py:779-795) with request_profile and the snapshot token sets: the five ordinary wordings return 2, the four expanding ones set shape_expanding and return None; tests/test_ordinary_ask_unit_ceiling.py:28-50 pins them and the evidence log shows both PASSED. |
| 2 | satisfied | `AR-438.2-20260911-2ae0a837` | `2a49d9a987e36f42135974852bcefd917a25419e1b618d316f78932cd7840da6` | 2026-09-11 | pipeline.py:1179-1209 returns the canary/inquiry one-unit contracts before applying the ceiling as max_planned_units; the route at 2184-2188 passes request.user_message; test_ordinary_ask_unit_ceiling.py:73-108 and test_activation_canary_contract.py:283,596-603 pin both; fast spine: 1152 passed. |
| 3 | satisfied | `AR-438.3-20260911-3f486880` | `c05cd7b991b973b2081f44370fa64214b424f528550e613460be3d25090a3927` | 2026-09-11 | AR-438-four-host-measurement-20260911.json shows post-reinstall runs on claude, hermes, zcode, openclaw each with planned_units 2 and staffing accepted, staffed "4 of 4" versus the 2026-09-11 pre-change batch "1 of 4"; the fifth host codex is activation-required, corroborated in repo docs. |
