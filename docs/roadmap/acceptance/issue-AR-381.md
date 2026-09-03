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
candidate_commit: pending
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
| 1 | file | `the nine prose fields take the case flag; the allowlisted lists and tools do not` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:643-690` |
| 1 | file | `PROSE_CASE_PRESERVING_SCHEMA_VERSION is frozen at 4 rather than tracking the current version` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:29-34` |
| 1 | test | `test_contract_prose_keeps_its_authored_case_at_v4 over all nine prose fields` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:784-797` |
| 1 | command-output | `every prose section of the packaged card renders its authored case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:4-27` |
| 2 | file | `the projected outcomes tuple is normalized for the exact-set duplicate check` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1519-1526` |
| 2 | file | `routing identifiers are normalized before the lowercase-only pattern match` | 2026-09-02 | `agency_runtime/core/workforce/hiring.py:1505-1514` |
| 2 | test | `test_identifier_lists_still_casefold over tools, lifecycle_phases, platforms and hosts` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:576-595` |
| 2 | test | `test_projected_outcomes_are_normalized_for_duplicate_detection` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3177-3189` |
| 2 | test | `test_routing_identifiers_survive_case_preserved_artifacts` | 2026-09-02 | `tests/test_workforce_dynamic_hiring.py:3192-3204` |
| 2 | command-output | `workforce outcomes and artifact_kinds stay normalized while platforms and hosts stay casefolded` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:29-32` |
| 3 | test | `test_packaged_cards_render_prose_in_its_authored_case` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:828-840` |
| 3 | command-output | `Python source, Async Python design and CLIs all render with their authored case` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:5-20` |
| 4 | file | `the package-v3 predecessor keeps an already-installed v3 contractor upgradable` | 2026-09-02 | `agency_runtime/core/workforce/known_installer.py:366-383` |
| 4 | test | `test_contract_prose_still_casefolds_at_v3` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:798-811` |
| 4 | test | `test_v3_contract_compiles_through_the_v3_template pins the v3 prompt hash as a literal` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:813-826` |
| 4 | command-output | `all fifteen packaged contracts replay both their v2 and their v3 prompt hash` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-381-evidence-20260902.txt:34-36` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
