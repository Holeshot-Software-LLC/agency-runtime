---
title: "AR-382 acceptance verification record"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-382-predecessor-projection-keeps-the-current-version-case.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-382
candidate_commit: pending
evidence_cutoff: 2026-09-03
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/573
---

# AR-382 acceptance verification record

Each predecessor package is now re-parsed at its own schema version rather than
relabelled, so the dataclass the projection reads folds exactly as that version
folded. Proven live against the real Store: the same box that reported
`15 preserved` before the fix reports `15 upgraded` after it.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `_legacy_known_contractor_package re-parses at v1 instead of relabelling` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:317-348` |
| 1 | file | `_v2_known_contractor_package re-parses at v2` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:351-375` |
| 1 | file | `_v3_known_contractor_package re-parses at v3` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:378-400` |
| 1 | test | `test_predecessor_projections_reparse_at_their_own_version walks all 15 contractors and every predecessor below the case-preserving version, asserting both the contract scenarios and the projected not_for and scope_qualifiers are casefolded` | 2026-09-03 | `tests/test_known_contractor_install.py:899-930` |
| 2 | command-output | `before the fix a real install reported 0 upgraded and 15 preserved, with detail.recruitment_contract the only failing clause` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:5-15` |
| 2 | command-output | `after the fix the same box and Store report 15 upgraded and 0 preserved` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:17-19` |
| 2 | command-output | `the roster now serves package-v4-7d4e81649e190a80 with case-preserved prose` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:21-24` |
| 3 | file | `each builder pins its historical prompt hashes and raises RuntimeError on drift: v1` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:99-121` |
| 3 | file | `the v2 pinned table` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:122-143` |
| 3 | file | `the v3 pinned table` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:144-165` |
| 3 | test | `test_v2_contract_compiles_through_the_v2_template_not_the_current_one pins the v2 prompt hash as a literal` | 2026-09-03 | `tests/test_workforce_hiring_contract.py:675-688` |
| 3 | test | `test_v3_contract_compiles_through_the_v3_template pins the v3 prompt hash as a literal` | 2026-09-03 | `tests/test_workforce_hiring_contract.py:839-851` |
| 3 | command-output | `all 60 predecessor packages build with zero prompt-hash drift against the three pinned tables` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:30-33` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
