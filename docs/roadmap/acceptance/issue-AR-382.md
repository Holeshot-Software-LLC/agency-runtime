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
candidate_commit: 4cb6a1634b65726d40b981cc1b3f8edcc57c9beb
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
| 1 | test | `test_predecessor_projections_reparse_at_their_own_version asserts both the contract scenarios and the projected not_for and scope_qualifiers are casefolded` | 2026-09-03 | `tests/test_known_contractor_install.py:899-930` |
| 1 | file | `_known_contractor_predecessor_packages returns every predecessor version: v1, the malformed v1 identity, v2 and v3` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:422-433` |
| 1 | test | `test_known_contractor_set_is_exact_bounded_and_immediately_enabled pins the packaged set at exactly 15` | 2026-09-03 | `tests/test_workforce_hiring_contract.py:75-95` |
| 1 | command-output | `60 predecessor packages build across the 15 contractors, i.e. all four versions each` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:30-33` |
| 2 | command-output | `before the fix a real install reported 0 upgraded and 15 preserved, with detail.recruitment_contract the only failing clause` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:5-15` |
| 2 | file | `the reproducible demo seeds an isolated Store at package-v2 then runs install_known_contractors` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-upgrade-demo.py:1-33` |
| 2 | command-output | `seeded at v2, the installer reports upgraded=15 preserved=0 and the workers end at v4` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:35-39` |
| 2 | command-output | `the live roster serves package-v4-7d4e81649e190a80 with case-preserved prose` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:21-24` |
| 3 | file | `each builder pins its historical prompt hashes and raises RuntimeError on drift: v1` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:99-121` |
| 3 | file | `the v2 pinned table` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:122-143` |
| 3 | file | `the v3 pinned table` | 2026-09-03 | `agency_runtime/core/workforce/known_installer.py:144-165` |
| 3 | test | `test_v2_contract_compiles_through_the_v2_template_not_the_current_one pins the v2 prompt hash as a literal` | 2026-09-03 | `tests/test_workforce_hiring_contract.py:675-688` |
| 3 | test | `test_v3_contract_compiles_through_the_v3_template pins the v3 prompt hash as a literal` | 2026-09-03 | `tests/test_workforce_hiring_contract.py:839-851` |
| 3 | command-output | `all 60 predecessor packages build with zero prompt-hash drift against the three pinned tables` | 2026-09-03 | `docs/roadmap/acceptance/evidence/AR-382-evidence-20260903.txt:30-33` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
