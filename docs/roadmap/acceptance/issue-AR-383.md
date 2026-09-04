---
title: "AR-383 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0208-carry-the-inferred-subject-beside-the-turn-context.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-383
candidate_commit: pending
evidence_cutoff: 2026-09-04
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 acceptance verification record

Pending draft. The subject the runtime infers for a turn whose wording
retrieval cannot read travels beside the turn's projected routing context
rather than inside it, so the context a fresh turn projects stays the empty
projection and dense recall still runs; the subject reaches the planner
document, the per-unit recall query and the recruiter document; and a refused
projection names the validation that refused it with a closed code the
attempt and the receipt keep. Criterion 5 is evidenced by the same
thirty-four-prompt smoke as the 2026-09-03 measurement, re-run on the branch
runtime.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_with_inferred_subject returns the projected context unchanged and the hints beside it, so a fresh turn's context stays the empty projection; the stage cache revision digests the context and the subject together` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:4354-4413` |
| 1 | file | `project_turn_routing_context is unchanged in what it accepts: the same two shapes, now answered through one projector that also reports its refusal` | 2026-09-04 | `agency_runtime/core/turn_routing_context.py:223-232` |
| 1 | test | `test_a_fresh_turn_s_context_stays_projectable_and_the_subject_rides_beside asserts the merged shape is refused, that the fresh turn's empty context projects, and names the refusal` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:57-64` |
| 1 | test | `test_an_unreadable_request_keeps_dense_recall_and_both_documents_carry_the_subject drives planner, recall and recruiter on a request whose subject is inferred and asserts no skipped dense-recall attempt and an applied one` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:146-197` |
| 2 | file | `project_unit_query takes the inferred subject beside the context, prefers a prior turn's own hints, and renders the subject into the query text and its context revision` | 2026-09-04 | `agency_runtime/core/workforce/hybrid_recall.py:282-321` |
| 2 | file | `_effective_subject: the context's own subject wins, the inferred one is used only otherwise and is projected through the same guard` | 2026-09-04 | `agency_runtime/core/workforce/hybrid_recall.py:241-257` |
| 2 | file | `discover_hybrid_recall threads the inferred subject into every per-unit query` | 2026-09-04 | `agency_runtime/core/workforce/hybrid_recall.py:851-854` |
| 2 | test | `test_the_typed_subject_reaches_the_per_unit_recall_query asserts the rendered query text carries the inferred domains and languages, that the context revision changes with them, and that a prior turn's subject is not overwritten` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:93-114` |
| 2 | test | `test_an_unreadable_request_keeps_dense_recall_and_both_documents_carry_the_subject asserts every embedded unit query carries the inferred subject line and that both documents carry inferred_work_subject` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:146-197` |
| 3 | file | `TURN_ROUTING_CONTEXT_REJECTION_CODES: the closed set of reasons a context projection refuses a value` | 2026-09-04 | `agency_runtime/core/turn_routing_context.py:158-172` |
| 3 | file | `_project_turn_routing_context returns the code for each refusal, one per validation, carrying no request content` | 2026-09-04 | `agency_runtime/core/turn_routing_context.py:172-211` |
| 3 | file | `RecallProjectionError carries the reason code the query's projection refused with` | 2026-09-04 | `agency_runtime/core/workforce/hybrid_recall.py:233-238` |
| 3 | file | `the skipped dense-recall attempt records that code in validation_reason_codes and nothing from the exception's text` | 2026-09-04 | `agency_runtime/core/workforce/inference.py:2436-2455` |
| 3 | file | `the preflight-failure receipt admits exactly that closed set for the recall stages` | 2026-09-04 | `agency_runtime/core/preflight_failure.py:214-221` |
| 3 | test | `test_a_refused_projection_names_the_validation_on_the_attempt_and_the_receipt asserts the raised code, the attempt's validation_reason_codes, and that the receipt keeps the closed code and drops anything else` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:117-143` |
| 3 | test | `test_every_refusal_has_a_closed_code asserts a valid context projects with no code and that each refusal returns its own code from the closed set` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:67-90` |
| 4 | test | `test_a_fresh_turn_s_context_stays_projectable_and_the_subject_rides_beside pins the fresh-turn shape: the merged single-key mapping is refused, the empty projection is what a fresh turn carries` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:57-64` |
| 4 | test | `test_the_typed_subject_reaches_the_per_unit_recall_query pins that the subject reaches the query beside that context` | 2026-09-04 | `tests/test_inferred_subject_beside_context.py:93-114` |
| 4 | file | `the curated conformance mutations: merging the subject back into the context, and dropping the refusal code, are each killed by one of those tests` | 2026-09-04 | `agency_runtime/core/evals/decision_conformance.py:358-396` |
| 5 | command-output | `the thirty-four-prompt smoke re-run on the branch runtime: every prompt's subject stage and dense-recall attempts, with the 2026-09-03 baseline beside it` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-383-evidence-20260904.txt:22-72` |
| 5 | command-output | `the measurement setup and the baseline it is compared against` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-383-evidence-20260904.txt:1-6` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
