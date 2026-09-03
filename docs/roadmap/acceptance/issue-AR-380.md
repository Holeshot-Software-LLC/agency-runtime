---
title: "AR-380 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-380-execution-profile-prose-is-casefolded.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-380
candidate_commit: 328e8ef8911eeb39cff52bba4b8f02c5a670797f
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/564
---

# AR-380 acceptance verification record

Builder evidence for case-preserving execution-profile prose. AR-380 landed
inside the ADR-0196 contract version bump, as its own issue required, so the
case change is gated on schema version 3 and every earlier version renders
exactly as it did before.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_items takes a casefold flag; the identifier path is unchanged` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:487-505` |
| 1 | file | `_execution_items preserves case from v3 and explains why earlier versions must not` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:543-570` |
| 1 | file | `CASE_PRESERVING_SCHEMA_VERSION is frozen at 3 rather than tracking the current version` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:24-27` |
| 1 | test | `test_execution_profile_prose_keeps_its_authored_case_end_to_end` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:529-545` |
| 1 | test | `test_v1_and_v2_execution_prose_still_casefolds` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:548-568` |
| 1 | command-output | `a principle naming America/Chicago renders with its case and america/chicago is absent from the prompt` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-380-evidence-20260902.txt:8-10` |
| 2 | test | `test_identifier_lists_still_casefold_at_v3 over capabilities, tools, lifecycle_phases, platforms and hosts` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:567-579` |
| 2 | test | `test_identifier_lists_still_casefold_at_v3 is parametrized over the five identifier lists` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:567-570` |
| 2 | command-output | `all five identifier lists come back casefolded from an uppercased input at v3` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-380-evidence-20260902.txt:12-17` |
| 3 | file | `the filler blocklist compares item.casefold() while the stored value keeps its case` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:558-564` |
| 3 | file | `the uniqueness check compares a casefolded set so two spellings stay one value` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:500-502` |
| 3 | test | `test_generic_guidance_rejection_fires_on_case_varied_input` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:582-592` |
| 3 | test | `test_uniqueness_rejection_fires_on_case_varied_input` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:595-608` |
| 3 | command-output | `twelve case, casefold, uniqueness and generic-guidance cases pass under -W error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-380-evidence-20260902.txt:4-6` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-380.1-20260902-831cdf99` | `268f29405b161fae1f39c09a45b71bbd8d8d34099fc5c5119ee128208b98e8d8` | 2026-09-02 | The cited end-to-end test parses authored `America/Chicago` text and asserts the same case in the parsed profile and compiled prompt, while the command output confirms the preserved rendering and absence of the casefolded form. |
| 3 | satisfied | `AR-380.3-20260902-0475ffb2` | `4349a91424c92d7a4ee52b140b37af64c09beb8fdec01bad533a3ef153cea450` | 2026-09-02 | The two cited tests assert ValueError for case-varied generic guidance and case-only duplicate principles, and the cited pytest output reports all 12 selected cases passed. |
| 2 | satisfied | `AR-380.2-20260902-7a47e988` | `51af0d233e9374b22c0096e9ba12f6f2df8a9aa5edb2a637b8175702f85bec57` | 2026-09-02 | The parametrized test uppercases each of the five identifier lists, parses the contract, and asserts every resulting tuple equals the casefolded input. |
