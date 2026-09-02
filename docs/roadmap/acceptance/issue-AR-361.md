---
title: "AR-361 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-361-builder-evidence-isolated-verification.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-361
candidate_commit: 197bcae4b6a0843082b6f5522d5322bdf83994fe
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/434
---

# AR-361 acceptance verification record

The gate's own record, cited against its merged candidate `197bcae4`;
each verdict below is one isolated single-check run through the codex
transport of `scripts/verify_acceptance.py`.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `validate_acceptance_verification` | 2026-09-02 | `scripts/verify_docs.py:1583-1633` |
| 1 | file | `_acceptance_done_errors` | 2026-09-02 | `scripts/verify_docs.py:1553-1580` |
| 1 | test | `test_done_flip_requires_acceptance_record_unless_grandfathered` | 2026-09-02 | `tests/test_verify_docs_schema.py:1513-1521` |
| 1 | test | `test_acceptance_missing_verdict_or_builder_row_blocks_done_flip` | 2026-09-02 | `tests/test_verify_docs_schema.py:1550-1560` |
| 1 | test | `test_repository_pre_verification_history_is_frozen_and_consistent` | 2026-09-02 | `tests/test_verify_docs_schema.py:1822-1835` |
| 1 | file | `acceptance record lifecycle` | 2026-09-02 | `docs/roadmap/acceptance/README.md#lifecycle` |
| 2 | file | `verify_criterion` | 2026-09-02 | `scripts/verify_acceptance.py:412-472` |
| 2 | file | `_invoke_verifier` | 2026-09-02 | `scripts/verify_acceptance.py:316-345` |
| 2 | file | `record_verdict` | 2026-09-02 | `scripts/verify_acceptance.py:389-409` |
| 2 | file | `acceptance_evidence_digest` | 2026-09-02 | `scripts/verify_docs.py:1187-1210` |
| 2 | test | `test_runner_records_isolated_satisfied_verdicts_that_unlock_the_done_flip` | 2026-09-02 | `tests/test_verify_acceptance.py:181-226` |
| 2 | test | `test_acceptance_verifier_run_must_judge_exactly_one_criterion` | 2026-09-02 | `tests/test_verify_docs_schema.py:1596-1612` |
| 2 | test | `test_transport_grants_only_bounded_read_only_investigation_options` | 2026-09-02 | `tests/test_verify_acceptance.py:380-445` |
| 2 | file | `AR-363 record verdicts (real isolated runs)` | 2026-09-02 | `docs/roadmap/acceptance/issue-AR-363.md#verification` |
| 3 | test | `test_acceptance_absent_or_contradicted_verdict_blocks_done_flip` | 2026-09-02 | `tests/test_verify_docs_schema.py:1528-1547` |
| 3 | test | `test_runner_records_contradicted_verdicts_that_block_the_done_flip` | 2026-09-02 | `tests/test_verify_acceptance.py:263-281` |
| 3 | test | `test_runner_records_absent_builder_evidence_without_calling_a_model` | 2026-09-02 | `tests/test_verify_acceptance.py:284-311` |
| 3 | test | `test_acceptance_absent_builder_evidence_forces_absent_verdict` | 2026-09-02 | `tests/test_verify_docs_schema.py:1707-1722` |
| 3 | file | `AR-356 record: a real absent verdict blocking the flip` | 2026-09-02 | `docs/roadmap/acceptance/issue-AR-356.md#verification` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-361.1-20260902-1c37a83c` | `3ebb075f497f00f110e96c13e27189bb8a2b8bf5050c6de6d04300732c54fa05` | 2026-09-02 | The validator requires each done issue’s every criterion to have builder evidence, and the cited test confirms a missing criterion-2 builder row blocks the done flip. |
| 2 | satisfied | `AR-361.2-20260902-e79c88cb` | `8c6c1e8f1956559625caffc8df19a4e36a594cf6a9a9789a2bf8106ec3f573b5` | 2026-09-02 | verify_criterion builds one indexed case, _invoke_verifier calls once on a private snapshot, record_verdict stores that criterion's unique run and digest, and the cited tests enforce one criterion per run. |
| 3 | satisfied | `AR-361.3-20260902-a929aeea` | `d00cadf8ddaaf0cf3e306b853f846dadd08f92f78f4388de8b0debc5709bfc9d` | 2026-09-02 | The cited regression tests explicitly cover absent and contradicted verdicts, require absent builder evidence to yield an absent verdict, and confirm both verdicts block the done flip. |
