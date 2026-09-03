---
title: "AR-379 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-379-hire-schema-has-no-home-for-domain-procedure.md
  - docs/decisions/0196-carry-governed-method-and-an-output-exemplar-in-the-contractor-card.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-379
candidate_commit: pending
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/553
---

# AR-379 acceptance verification record

Builder evidence for governed method on the contractor card. The owner call was
made and recorded as ADR-0196: method is in scope, expressed only through the
closed schema. Criterion 2's regression case is deliberately structural rather
than a critic-prompt assertion, because a model gate cannot be pinned by a test.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `ADR-0196 records the decision, its three rejected alternatives, and the closed-profile posture it preserves` | 2026-09-02 | `docs/decisions/0196-carry-governed-method-and-an-output-exemplar-in-the-contractor-card.md:1-121` |
| 1 | file | `the decisions register carries ADR-0196 as accepted` | 2026-09-02 | `docs/decisions/README.md:151` |
| 1 | file | `output_exemplar is a top-level contract field at schema version 3` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:336` |
| 1 | file | `template v3 adds one Answer shape section and keeps v1 and v2 compiling unchanged` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:262-278` |
| 1 | test | `test_output_exemplar_is_required_bounded_and_rendered` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:657-675` |
| 1 | test | `test_template_hashes_are_pinned_per_version pins v1, v2 and v3 as literals` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:611-638` |
| 1 | test | `test_v2_contract_compiles_through_the_v2_template_not_the_current_one` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:641-654` |
| 1 | command-output | `all fifteen packaged contracts replay their v2 prompt hash byte-identically` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-379-evidence-20260902.txt:19-20` |
| 2 | file | `the fifteen packaged cards carry a distinct authored exemplar` | 2026-09-02 | `agency_runtime/core/workforce/known_contractors.py:354-421` |
| 2 | file | `working_principles carries a structural minimum of two items from v3` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:543-570` |
| 2 | file | `the hiring critic refuses a governed-but-generic card, as ADR-0196 decision 4 requires` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:142-146` |
| 2 | test | `test_single_maxim_working_principles_is_rejected_at_v3` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:699-708` |
| 2 | test | `test_packaged_exemplars_are_distinct_and_reach_every_prompt` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:725-734` |
| 2 | test | `test_adr0196_card_quality_rules_reach_every_gate` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3137-3152` |
| 2 | command-output | `a packaged card renders an ordered two-step procedure and a concrete answer shape` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-379-evidence-20260902.txt:4-9` |
| 2 | command-output | `a single-maxim principle set is rejected at v3 and still replays at v2` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-379-evidence-20260902.txt:11-13` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
