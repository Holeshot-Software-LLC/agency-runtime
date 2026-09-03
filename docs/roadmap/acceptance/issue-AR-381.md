---
title: "AR-381 acceptance verification record"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-381-contract-prose-outside-the-execution-profile-is-casefolded.md
  - docs/roadmap/issue-AR-380-execution-profile-prose-is-casefolded.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-381
candidate_commit: b99cdfd37482b10f08de3d5d4cd3b9aa39b3d953
evidence_cutoff: 2026-09-02
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/568
---

# AR-381 acceptance verification record

Builder evidence for case-preserving contract prose at schema version 4. The
per-field audit corrected two of the issue's own premises: `capabilities` is not
matched against `unit.required_capabilities`, and the real constraints are two
projection boundaries rather than the stored fields. Both are normalized at the
projection, so the card renders authored case while every matcher still sees one
spelling.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `the nine prose fields take the case flag; the allowlisted lists and tools do not` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:643-708` |
| 1 | file | `PROSE_CASE_PRESERVING_SCHEMA_VERSION is frozen at 4 rather than tracking the current version` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:29-34` |
| 1 | file | `_PROSE_FIELDS names the nine fields the case tests are parametrized over` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:789-799` |
| 1 | test | `test_contract_prose_keeps_its_authored_case_at_v4 with its parametrize decorator, one run per prose field` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:809-821` |
| 1 | command-output | `every prose section of the packaged card renders its authored case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:4-27` |
| 2 | file | `the projected outcomes tuple is normalized for the exact-set duplicate check` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1519-1526` |
| 2 | file | `routing identifiers are normalized before the lowercase-only pattern match` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1505-1514` |
| 2 | test | `test_every_contract_list_field_is_either_case_preserved_or_casefolded asserts the split is a partition over every string-tuple field` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:926-952` |
| 2 | file | `_CASEFOLDED_FIELDS names the four fields that keep normalized casing` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:910-924` |
| 2 | test | `test_projected_outcomes_are_normalized_for_duplicate_detection names _axis_subset as the consumer` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3177-3189` |
| 2 | test | `test_routing_identifiers_survive_case_preserved_artifacts names the routing extraction as the consumer for tools and artifacts` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3192-3204` |
| 2 | command-output | `workforce outcomes and artifact_kinds stay normalized while platforms and hosts stay casefolded` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:29-32` |
| 3 | test | `test_packaged_cards_render_prose_in_its_authored_case compares every rendered prose section of all 15 cards against the stored values by equality` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:854-885` |
| 3 | file | `_PROPER_NOUNS lists the proper nouns the packaged corpus uses` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:911-923` |
| 3 | test | `test_no_packaged_card_renders_a_lowercased_proper_noun scans all five rendered sections of every card, excluding tool ids by identity` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:954-984` |
| 3 | command-output | `Python source, Async Python design and CLIs all render with their authored case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:5-20` |
| 3 | command-output | `the 23 case tests pass under -W error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:42-44` |
| 3 | command-output | `corpus-wide scan: 15 cards x 5 sections, 256 bullets, 11 proper nouns, 0 lowercased hits` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:46-47` |
| 4 | file | `the package-v3 predecessor keeps an already-installed v3 contractor upgradable` | 2026-09-02 | `agency_runtime/core/workforce/known_installer.py:366-383` |
| 4 | test | `test_contract_prose_still_casefolds_at_v3` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:823-835` |
| 4 | test | `test_v3_contract_compiles_through_the_v3_template pins the v3 prompt hash as a literal` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:838-850` |
| 4 | command-output | `all fifteen packaged contracts replay both their v2 and their v3 prompt hash` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:34-36` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 3 | satisfied | `AR-381.3-20260902-280ed40e` | `aa0a0dd97f7187f586f9ebfa90cab77634f8df036a576e99fe6b35e6afb564f0` | 2026-09-02 | The corpus-wide parametrized test scans all five rendered sections across every packaged card for 11 listed proper nouns, and the cited run passed with 256 bullets scanned and zero lowercased hits. |
| 1 | satisfied | `AR-381.1-20260902-ba065b70` | `4a70c6373af683a3f3c089ba30bdb40cd37c43999ff59e0856c5be91ac2ca938` | 2026-09-02 | The parser applies case preservation to all nine enumerated prose fields at schema v4, and the parametrized test asserts each field retains its mixed-case authored value; packaged-card output also shows preserved casing. |
| 2 | satisfied | `AR-381.2-20260902-ffec0346` | `cf427ed4d658bd5287ae9ee13242b43fa35f0cf42cb71c83f6ba0ab649d8fb28` | 2026-09-02 | The cited tests exhaustively partition string-tuple fields, name allowlist, routing, and duplicate-check consumers, and assert casefolding for contract fields, projected outcomes, and artifact identifiers. |
| 4 | satisfied | `AR-381.4-20260902-fbb6db4b` | `08fa58dbd5386428236e3dcc7a809c6256113c41366ddc847e07dd0d96e7a95c` | 2026-09-02 | The cited replay artifact reports zero prompt-hash mismatches for all 15 packaged contracts under both v2 and v3, and the v3 regression test pins an exact historical prompt hash. |
