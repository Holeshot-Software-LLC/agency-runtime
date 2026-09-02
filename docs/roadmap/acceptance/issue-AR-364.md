---
title: "AR-364 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-364-audit-external-review-cards.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-364
candidate_commit: 57b3152c6c3090679a10894edc122d401c5d4947
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/437
---

# AR-364 acceptance verification record

ECC review cards audited into the governed roster: builder evidence cited by
the integrator against the merged candidate `57b3152c` (the AR-364 merge
`d024add4` plus its captured command output); every verdict below comes from
one isolated single-check verifier run (`scripts/verify_acceptance.py`, codex
transport) that saw only that criterion and its own rows.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `silent-failure-hunter audit contract: source ecc, content_hash, source_revision ca185ef5, audit_revision 2` | 2026-09-02 | `docs/roster-audit/batch-ecc-review.json:2-71` |
| 1 | file | `type-design-analyzer audit contract: source ecc, content_hash, source_revision ca185ef5, audit_revision 2` | 2026-09-02 | `docs/roster-audit/batch-ecc-review.json:72-141` |
| 1 | file | `audit manifest sources.ecc: repository, origin, pinned revision, MIT, explicit inventory` | 2026-09-02 | `docs/roster-audit/audit-manifest.json:21-27` |
| 1 | file | `packaged manifest entry silent-failure-hunter with source_repository and source_revision` | 2026-09-02 | `agency_runtime/core/roster/data/manifest.json:15903-15975` |
| 1 | file | `packaged manifest entry type-design-analyzer with source_repository and source_revision` | 2026-09-02 | `agency_runtime/core/roster/data/manifest.json:18343-18415` |
| 1 | file | `audit review: two of two approved, findings and dispositions` | 2026-09-02 | `docs/roster-audit/batch-ecc-review-review.md:18-44` |
| 1 | test | `test_cards_are_pinned_to_the_ecc_source_and_review_only` | 2026-09-02 | `tests/test_ecc_review_cards.py:88-116` |
| 1 | command-output | `pytest: the provenance test PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-364-evidence-20260902.txt:1-11` |
| 2 | file | `curated retrieval probes silent-failure-review and type-design-review (direct, required card, max rank 10)` | 2026-09-02 | `agency_runtime/core/evals/full_roster_cases.py:24-48` |
| 2 | test | `test_curated_retrieval_covers_hard_negatives_multi_intent_and_abstention` | 2026-09-02 | `tests/test_full_roster_eval.py:109-134` |
| 2 | test | `test_cards_have_direct_retrieval_probes_in_the_curated_eval` | 2026-09-02 | `tests/test_ecc_review_cards.py:119-129` |
| 2 | command-output | `full-roster eval: both probes pass with required rank 1 and no forbidden card above; 9/9 curated cases` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-364-evidence-20260902.txt:12-19` |
| 3 | file | `_authority_satisfies: review authority never satisfies a modify unit` | 2026-09-02 | `agency_runtime/core/workforce/staffing_verifier.py:268-311` |
| 3 | file | `_unit_compatibility_reasons adds agent_authority_mismatch` | 2026-09-02 | `agency_runtime/core/workforce/staffing_verifier.py:342-360` |
| 3 | file | `packaged silent-failure-hunter: authority review, context_mode direct_safe` | 2026-09-02 | `agency_runtime/core/roster/data/manifest.json:15909-15927` |
| 3 | file | `packaged type-design-analyzer: authority review, context_mode direct_safe` | 2026-09-02 | `agency_runtime/core/roster/data/manifest.json:18349-18367` |
| 3 | test | `test_cards_cannot_staff_implementation_authority_work` | 2026-09-02 | `tests/test_ecc_review_cards.py:132-186` |
| 3 | command-output | `pytest: both parametrized authority-boundary runs PASSED at the candidate` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-364-evidence-20260902.txt:7-8` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-364.1-20260902-b589e6ad` | `3460da396cb631cdcfd53d4fb5236440d5687dd7890d1073e6162730c620f411` | 2026-09-02 | The audit excerpts identify both cards with the specified SHA-256 hashes, pinned ECC repository revision, audit revision 2, and approved status, while the packaged manifest excerpts preserve source_repository, source_revision, source_content_hash, and audit_revision for both. |
| 2 | satisfied | `AR-364.2-20260902-4e8392fb` | `2012eb7a0afe8ea367fdf03cee52b9d498f60f2b97060c138dcbec6da57205d3` | 2026-09-02 | The cited command output shows both matching direct probes ranked their required cards first, with no forbidden card above them, and reports all 9 curated cases passed. |
| 3 | satisfied | `AR-364.3-20260902-97b89cc6` | `d1f1073a99fded158633505562bb9f00dfce2bc198ed3be1b7a75398b12a997c` | 2026-09-02 | The parametrized test excerpt verifies both cards have review authority, are rejected for modify implementation work with agent_authority_mismatch, and both cited test runs passed. |
