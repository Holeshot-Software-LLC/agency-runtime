---
title: "AR-357 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-357-canonical-response-contract-statement.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-357
candidate_commit: 50e74432e766ff27ef585c54fe4919f91bd7a12b
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/427
---

# AR-357 acceptance verification record

One canonical response contract per turn: builder evidence cited by the
integrator against the merged candidate `50e74432` (the AR-357 merge
`c1a5fbd6` plus its captured command output); every verdict below comes from
one isolated single-check verifier run (`scripts/verify_acceptance.py`, codex
transport) that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `RESPONSE_CONTRACT_TEXT and its SHA-256 pin: the one statement of what the finalizer checks` | 2026-09-02 | `agency_runtime/core/header/response_contract.py:35-48` |
| 1 | file | `response_contract_context: the block delivered once per turn` | 2026-09-02 | `agency_runtime/core/header/response_contract.py:65-70` |
| 1 | file | `every header snapshot instruction carries SNAPSHOT_VALUES_ONLY_NOTE instead of its own expectation` | 2026-09-02 | `agency_runtime/core/header/snapshot.py:20-31` |
| 1 | file | `claude/codex/zcode hook states the contract once beside the turn's first values` | 2026-09-02 | `agency_runtime/adapters/hooks.py:2577-2591` |
| 1 | test | `test_the_contract_text_is_pinned_and_states_only_what_is_verified` | 2026-09-02 | `tests/test_response_contract.py:101-118` |
| 1 | test | `test_every_snapshot_instruction_says_it_carries_values_only` | 2026-09-02 | `tests/test_response_contract.py:119-125` |
| 1 | test | `test_the_contract_is_delivered_once_beside_the_turns_first_values` | 2026-09-02 | `tests/test_response_contract.py:243-258` |
| 1 | command-output | `pytest: the delivery test PASSED on both hosts at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-357-pytest-20260902.txt:13-16` |
| 2 | file | `root cause and the two measured shapes, recorded with the fix` | 2026-09-02 | `docs/roadmap/issue-AR-357-canonical-response-contract-statement.md#implementation-2026-09-02` |
| 2 | file | `_unreadable_snapshot_result: unreadable evidence is Agency's fault, not a missing requirement` | 2026-09-02 | `agency_runtime/core/header/finalize.py:251-282` |
| 2 | file | `_unverifiable_decision: a verifier-evidence-only violation becomes verification_unavailable` | 2026-09-02 | `agency_runtime/core/header/contract.py:1141-1163` |
| 2 | file | `header_snapshot_unavailable_context: the honest replacement for a snapshot that did not render` | 2026-09-02 | `agency_runtime/core/header/response_contract.py:71-89` |
| 2 | test | `test_unreadable_evidence_publishes_unverified_instead_of_naming_a_requirement` | 2026-09-02 | `tests/test_response_contract.py:201-222` |
| 2 | test | `test_a_turn_whose_snapshot_cannot_render_is_told_so` | 2026-09-02 | `tests/test_response_contract.py:259-268` |
| 2 | command-output | `pytest: both regression shapes PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-357-pytest-20260902.txt:10-16` |
| 3 | file | `split_missing_requirements: the vocabulary split between delivered requirements and other codes` | 2026-09-02 | `agency_runtime/core/header/contract.py:92-115` |
| 3 | file | `verification_is_unavailable: only verifier evidence codes` | 2026-09-02 | `agency_runtime/core/header/contract.py:126-134` |
| 3 | file | `terminal_rejection_reason names the unmet contract lines` | 2026-09-02 | `agency_runtime/core/header/finalize.py:114-129` |
| 3 | file | `stored_missing_requirements: a replayed rejection names the same lines` | 2026-09-02 | `agency_runtime/core/header/finalize.py:93-113` |
| 3 | test | `test_a_rejection_names_only_requirements_the_contract_stated` | 2026-09-02 | `tests/test_response_contract.py:143-168` |
| 3 | test | `test_missing_vocabulary_splits_delivered_requirements_from_agency_faults` | 2026-09-02 | `tests/test_response_contract.py:126-142` |
| 3 | test | `test_a_replayed_rejection_names_the_same_lines_as_the_original` | 2026-09-02 | `tests/test_response_contract.py:169-180` |
| 3 | command-output | `pytest: the rejection-vocabulary tests PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-357-pytest-20260902.txt:7-16` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-357.1-20260902-848a2d14` | `5d228a0f5c6c73a68604c57c3a81dee3a1fd446c3620de63f10bbd537c343211` | 2026-09-02 | The canonical contract text is inserted once before the initial values, snapshots explicitly carry values only, and the cited delivery test asserts one marker per turn and passed for the tested hosts. |
| 2 | satisfied | `AR-357.2-20260902-146056cf` | `92362bf69ce6a9bdd51a4c3950d08b8196428af6efeacabb6a81f2e444756bde` | 2026-09-02 | The implementation note identifies the 2026-09-01 root cause, both named regression tests are shown, and the cited pytest output records both measured shapes passing. |
| 3 | satisfied | `AR-357.3-20260902-aba895aa` | `3c493c0aaa5fbe297d09c5d864f907dff2da564fa6d8a5f649d51e20d76fb42f` | 2026-09-02 | The cited implementation filters missing entries through DELIVERED_REQUIREMENTS, and both named tests passed while confirming Agency-side codes are excluded from rejection labels. |
