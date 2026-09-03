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
candidate_commit: 93719f58bf1e8b3d13a321ecdf1afcb4e29d4901
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
| 1 | file | `the nine prose fields take the case flag; the allowlisted lists and tools do not` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:643-692` |
| 1 | file | `PROSE_CASE_PRESERVING_SCHEMA_VERSION is frozen at 4 rather than tracking the current version` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:29-34` |
| 1 | file | `_PROSE_FIELDS names the nine fields the case tests are parametrized over` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:772-782` |
| 1 | test | `test_contract_prose_keeps_its_authored_case_at_v4, one run per prose field` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:793-804` |
| 1 | command-output | `every prose section of the packaged card renders its authored case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:4-27` |
| 2 | file | `the projected outcomes tuple is normalized for the exact-set duplicate check` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1519-1526` |
| 2 | file | `routing identifiers are normalized before the lowercase-only pattern match` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1505-1514` |
| 2 | test | `test_allowlisted_identifier_lists_are_still_checked_against_their_allowlist names the allowlist consumer for platforms, hosts and lifecycle_phases` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:866-885` |
| 2 | test | `test_projected_outcomes_are_normalized_for_duplicate_detection names _axis_subset as the consumer` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3177-3189` |
| 2 | test | `test_routing_identifiers_survive_case_preserved_artifacts names the routing extraction as the consumer for tools and artifacts` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3192-3204` |
| 2 | command-output | `workforce outcomes and artifact_kinds stay normalized while platforms and hosts stay casefolded` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:29-32` |
| 3 | test | `test_packaged_cards_render_prose_in_its_authored_case checks all 15 cards x every item of every prose field, with a floor so a vacuous pass fails` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:836-863` |
| 3 | file | `_RENDERED_PROSE_FIELDS separates the fields the template renders from the selection metadata it does not` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:785-790` |
| 3 | command-output | `Python source, Async Python design and CLIs all render with their authored case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:5-20` |
| 4 | file | `the package-v3 predecessor keeps an already-installed v3 contractor upgradable` | 2026-09-02 | `agency_runtime/core/workforce/known_installer.py:366-383` |
| 4 | test | `test_contract_prose_still_casefolds_at_v3` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:807-818` |
| 4 | test | `test_v3_contract_compiles_through_the_v3_template pins the v3 prompt hash as a literal` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:821-833` |
| 4 | command-output | `all fifteen packaged contracts replay both their v2 and their v3 prompt hash` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:34-36` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | absent | `AR-381.1-20260902-d326373b` | `ef74e32563d7dfbd53674b82f3ba786691ebcde0f38eb79df9b604fb8da22794` | 2026-09-02 | The excerpts list nine prose fields, but the shown test lacks its parametrization decorator and the parser excerpt shows case handling for only six, so end-to-end preservation for every field is not proven. |
| 2 | satisfied | `AR-381.2-20260902-2090d5bc` | `44188420dbbc4d7d6d4b0160ec2406c0778d3e4f401390258e2a8d4f2e18ffd8` | 2026-09-02 | The cited tests name and exercise allowlist matching for platforms, hosts, and lifecycle phases, _axis_subset deduplication for outcomes, and routing extraction/persistence for artifact kinds, with implementation excerpts showing casefolding. |
| 3 | absent | `AR-381.3-20260902-148ad1d9` | `92ac861db73b92324b03dc5ea6962ef926c956ed1116ad21fb6563125a6de506` | 2026-09-02 | The cited test only rejects fully casefolded bullet items and explicitly permits lowercase text mid-sentence, so it does not establish that no proper noun is lowercased in any section. |
| 4 | satisfied | `AR-381.4-20260902-4c3dd44a` | `d3aabeb74f326de767fa572da3aa8d55e71b0f32d566e7ac5f3023b28d6c362f` | 2026-09-02 | The replay artifact reports zero prompt-hash mismatches for all 15 packaged v2 and v3 contracts, reinforced by the pinned v3 compilation hash test and version-specific reconstruction code. |
