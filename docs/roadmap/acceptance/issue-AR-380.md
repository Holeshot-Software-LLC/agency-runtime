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
candidate_commit: pending
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
| 2 | test | `test_identifier_lists_still_casefold_at_v3 over capabilities, tools, lifecycle_phases, platforms and hosts` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:571-579` |
| 2 | command-output | `all five identifier lists come back casefolded from an uppercased input at v3` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-380-evidence-20260902.txt:12-17` |
| 3 | file | `the filler blocklist compares item.casefold() while the stored value keeps its case` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:558-564` |
| 3 | file | `the uniqueness check compares a casefolded set so two spellings stay one value` | 2026-09-02 | `agency_runtime/core/workforce/hiring_contract.py:500-502` |
| 3 | test | `test_generic_guidance_rejection_fires_on_case_varied_input` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:582-592` |
| 3 | test | `test_uniqueness_rejection_fires_on_case_varied_input` | 2026-09-02 | `tests/test_workforce_hiring_contract.py:595-608` |
| 3 | command-output | `twelve case, casefold, uniqueness and generic-guidance cases pass under -W error` | 2026-09-02 | `docs/roadmap/acceptance/evidence/AR-380-evidence-20260902.txt:4-6` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
