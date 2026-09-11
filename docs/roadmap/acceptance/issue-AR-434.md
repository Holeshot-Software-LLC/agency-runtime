---
title: "AR-434 acceptance verification record"
status: active
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [acceptance, workforce, planner, plan-policy]
related:
  - docs/roadmap/issue-AR-434-plan-policy-reads-a-handoff-request-as-a-code-mutation.md
  - docs/decisions/0250-read-a-prose-artefact-request-as-documentation-work.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-434
candidate_commit: f31ad2a85526e55a2bed3aca408b54b144d7a2d4
evidence_cutoff: 2026-09-11
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/848
---

# AR-434 acceptance verification record

## Builder evidence

The builder cites observations and does not judge. Scope is the prose-artefact
reading in `plan_policy` (ADR-0250), its regressions, and one fresh native run
per installed host on the exact observed handoff wording after the PR #866
reinstall. Each live observation is a single sample; the planner and recruiter
are stochastic. The 2026-09-10 diagnostic that reproduced the three lifecycle
repair codes is the reference, not a controlled baseline. One zcode turn
ended `response_invalid` on the finalization header check after its staffing
was accepted; that is recorded, not explained away.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `prose_artifact_request` binds every mutation verb to a prose object, refuses strong code verbs, and allows only locative code nouns | 2026-09-11 | agency_runtime/core/workforce/plan_policy.py:145-164 |
| 1 | file | Prose-artefact, locative-code, strong-verb and code-noun vocabularies | 2026-09-11 | agency_runtime/core/workforce/plan_policy.py:90-142 |
| 1 | file | Deterministic planner reads the same predicate on the raw request | 2026-09-11 | agency_runtime/core/workforce/fallback.py:322-331 |
| 1 | test | Observed wording plans documentation plus review and passes the policy; a code plan for it is refused; strong verb, non-locative object and change-verb-on-code keep the code shape | 2026-09-11 | tests/test_handoff_is_documentation.py:26-129 |
| 1 | test | Policy and deterministic planner agree on every wording; attributive prose nouns are not objects | 2026-09-11 | tests/test_handoff_is_documentation.py:131-175 |
| 1 | command-output | Focused regressions pass | 2026-09-11 | docs/roadmap/evidence/AR-434-focused-tests-20260911.txt:1-16 |
| 2 | file | Planner acceptance contract states the prose-artefact rule and its guard | 2026-09-11 | agency_runtime/core/workforce/plan_policy.py:414-420 |
| 2 | test | Negated scope still applies before the prose rule; existing documentation and code classification unchanged | 2026-09-11 | tests/test_handoff_is_documentation.py:73-87 |
| 2 | command-output | Focused regressions pass | 2026-09-11 | docs/roadmap/evidence/AR-434-focused-tests-20260911.txt:1-16 |
| 2 | command-output | Named fast spine passes on the final branch tip | 2026-09-11 | docs/roadmap/evidence/AR-434-fast-spine-20260911.txt:18-18 |
| 2 | command-output | Decision conformance kills all 188 mutations on the final branch tip | 2026-09-11 | docs/roadmap/evidence/AR-434-decision-conformance-20260911.json:1-13 |
| 3 | file | Runtime, exact request, its store fingerprint and the three lifecycle repair codes under test | 2026-09-11 | docs/roadmap/evidence/AR-434-handoff-diagnostic-20260911.json:6-36 |
| 3 | file | Five counted runs (claude, hermes, zcode, openclaw, codex): two units documentation then review-report, staffing accepted, every planner attempt applied, `lifecycle_repair_codes_seen` empty, no failure receipt | 2026-09-11 | docs/roadmap/evidence/AR-434-handoff-diagnostic-20260911.json:37-379 |
| 3 | file | Six captured critic packets, each `approved` true with empty reason codes | 2026-09-11 | docs/roadmap/evidence/AR-434-handoff-diagnostic-20260911.json:380-449 |
| 3 | file | Discarded killed openclaw run, excluded unrelated runs, the 2026-09-10 reference and the findings | 2026-09-11 | docs/roadmap/evidence/AR-434-handoff-diagnostic-20260911.json:450-562 |
| 3 | file | 2026-09-10 diagnostic: the planner first reply was rejected with the three codes in both modes | 2026-09-11 | docs/roadmap/evidence/AR-433-live-diagnostic-20260910.json:9-9 |
| 3 | receipt | claude run, preflight ready, documentation plus review | 2026-09-11 | 8d2e0f27-97bf-479e-b177-351b2f7d9e38 |
| 3 | receipt | codex run, preflight ready, documentation plus review, first live codex turn after the trust screen | 2026-09-11 | 5020d5af-dd5d-496f-8eb6-d475895a8ba2 |
| 3 | tracker | Tracker issue for parity | 2026-09-11 | https://github.com/Holeshot-Software-LLC/agency-runtime/issues/848 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-434.1-20260911-b1ec03d3` | `85856ba0e5d145a19368006e768d9e74ce46e47ac4f113b15d208755a055c04d` | 2026-09-11 | plan_policy.py:145-164 and request_profile (l.711-724) make the observed wording a docs mutation, not code_mutation; fallback.py:322-331 mirrors it; tests/test_handoff_is_documentation.py:44-56,95,150-164 keep "create the code" and "create a memo parser" code mutations, all PASSED in the log. |
| 2 | satisfied | `AR-434.2-20260911-bbfc31f6` | `fc78e7360461370cd4b407db5e2f15058e5c0b482e6c5d4896b2b81544b7d669` | 2026-09-11 | AR-434-focused-tests-20260911.txt shows 15 passes matching tests in tests/test_handoff_is_documentation.py, AR-434-fast-spine-20260911.txt ends 1152 passed/3 skipped, and prose_artifact_request appears only in plan_policy.py and fallback.py, leaving staffing, critic and validator code untouched. |
| 3 | satisfied | `AR-434.3-20260911-d7c44fc8` | `bc21b27ec52477b88e58c5dade54fcd3d239fcdedbd8929d7eeae3bfa17c7145` | 2026-09-11 | Snapshot AR-434-handoff-diagnostic-20260911.json shows five runs on the exact wording (request_sha256 equals store fingerprint), each staffing accepted with empty lifecycle_repair_codes_seen and no failure receipt; docs/worklog/README.md indexes the AR-434 commits and the roadmap row cites #848. |
