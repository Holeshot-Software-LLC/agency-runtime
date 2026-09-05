---
title: "AR-397 acceptance verification record"
status: active
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [acceptance, verification]
related:
  - docs/roadmap/issue-AR-397-packaged-contracts-cannot-be-revised-in-place.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-397
candidate_commit: 454329767720a87afb126cd033eb554e0f2d708d
evidence_cutoff: 2026-09-04
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/654
---

# AR-397 acceptance verification record

A packaged definition that shipped and was then revised in place is kept
verbatim as a superseded revision, pinned by prompt hash, and returned both as
an exact predecessor for the identity pass and as a metadata authority for the
repair pass. The implementation is `dda2c8a3` and `f67b718f`, merged in PR
#640; this record binds to a later commit that adds the evidence file and
cites the tree as it stands there.

Criteria 1, 3 and 4 are exercised by tests that seed a store at the superseded
identity and run the same passes `agency install` runs. Criteria 2 and 5 are
also read from a copy of the live store after the `c42fb0a5` install; the live
store was never opened for write.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | `every superseded revision is kept verbatim beside the current definition and parsed by the same helper` | 2026-09-04 | `agency_runtime/core/workforce/known_contractors.py:1088-1100` |
| 1 | file | `_known_contractor_predecessor_packages returns the template predecessors and the superseded revisions together` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:460-472` |
| 1 | file | `the identity pass accepts a worker whose stored prompt, version and recruitment contract match any predecessor, stages the current package, records an amend case and reports the worker upgraded; anything else is preserved` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:652-714` |
| 1 | test | `test_a_prompt_changing_revision_advances_from_its_superseded_identity seeds the superseded prompt, asserts upgraded, the current hash, the superseded prompt retained as a versioned prompt, and an idempotent second install` | 2026-09-04 | `tests/test_known_contractor_install.py:335-377` |
| 1 | command-output | `the five AR-397 tests pass at the candidate and all five fail on the pre-fix tree` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-397-evidence-20260904.txt:10-24` |
| 2 | file | `the current monitoring definition is built with the installation phase` | 2026-09-04 | `agency_runtime/core/workforce/known_contractors.py:1080` |
| 2 | file | `installation projects to the release lifecycle` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:89-97` |
| 2 | file | `the projected lifecycle tuple maps each definition phase through _LIFECYCLES` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:242` |
| 2 | test | `test_a_lifecycle_revision_reaches_the_live_contract_on_install asserts the shipped and current prompt hashes and metadata identities are equal, the worker is reported existing with no divergence, and the repair pass carries release into the recruitment contract and the index snapshot` | 2026-09-04 | `tests/test_known_contractor_install.py:289-332` |
| 2 | command-output | `on a copy of the live store after install: no divergence, recruitment contract lifecycle implementation and release, hire case auditable` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-397-evidence-20260904.txt:34-49` |
| 3 | file | `a superseded snapshot whose count or prompt hash does not match its pin raises before any package is built` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:441-458` |
| 3 | file | `install_known_contractors checks every superseded pin before the identity pass judges any worker, so a machine whose worker is already current stops too` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:593-606` |
| 3 | test | `test_a_drifted_superseded_pin_stops_the_install_on_a_current_machine installs cleanly, then drifts the pin and asserts the second install raises` | 2026-09-04 | `tests/test_known_contractor_install.py:427-443` |
| 3 | test | `test_superseded_packaged_identities_are_pinned_and_fail_closed pins the reconstruction to the table and asserts drifted and unpinned both raise through the predecessor path` | 2026-09-04 | `tests/test_known_contractor_install.py:446-473` |
| 4 | file | `known_contractor_revision_metadata_authorities names each superseded revision's metadata identity beside the current one` | 2026-09-04 | `agency_runtime/core/workforce/known_installer.py:475-497` |
| 4 | file | `_exact_packaged_revision accepts a stored metadata identity that matches any package-known authority, so the repair pass re-projects the contract instead of reporting revision_modified` | 2026-09-04 | `agency_runtime/core/store/workforce.py:1033-1053` |
| 4 | test | `test_a_metadata_only_revision_is_repaired_from_its_superseded_identity seeds a revision differing only in the positive scenario, asserts existing with no divergence, one contract repaired, and the current scope qualifiers on the snapshot` | 2026-09-04 | `tests/test_known_contractor_install.py:380-424` |
| 5 | test | `test_monitoring_engineer_covers_the_release_lifecycle asserts the definition's phases and the projected implementation and release lifecycles` | 2026-09-04 | `tests/test_operations_contractors.py:105-114` |
| 5 | command-output | `the release-lifecycle test passes at the candidate and fails on the pre-fix tree` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-397-evidence-20260904.txt:26-32` |
| 5 | command-output | `workforce_index_snapshot on a copy of the live store lists monitoring-engineer with lifecycle_phases implementation and release among 293 contracts` | 2026-09-04 | `docs/roadmap/acceptance/evidence/AR-397-evidence-20260904.txt:34-45` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-397.1-20260904-cc72dac5` | `ae151eca8b02c884aebc9b96e5a8ec669e888a4f20a470508c7f73fac18b0d9b` | 2026-09-04 | known_installer.py:628-715 advances a worker matching an exact superseded predecessor and reports it upgraded; test_known_contractor_install.py:335-377 seeds a prompt-changing superseded identity and asserts upgraded, the current hash, and the retained prompt, passing per the AR-397 evidence file. |
| 2 | satisfied | `AR-397.2-20260904-7953f0ad` | `8c3afe2ef4429a1d2d3805b922d864e572b5b73c47e840c458a7ea8de6d01d2a` | 2026-09-04 | tests/test_known_contractor_install.py:289-332 in the snapshot seeds the shipped identity and asserts slug in result.existing, packaged_workforce_divergence == (), and after reconcile the contract lifecycle == [implementation, release]; AR-397-evidence lines 39-43 show the same on the live store. |
| 3 | satisfied | `AR-397.3-20260904-5e509aeb` | `53c5449347d6720d21681127cd9659ae53dd0a6bb2561303f3bfda4d99319ae7` | 2026-09-04 | known_installer.py:441-457 raises on a superseded pin mismatch, and 600-606 runs that check for every slug before the identity pass that would short-circuit a current worker as existing; cmd_install reaches it via seed_starter_roster and installer.py:251, and both cited tests exist verbatim. |
| 4 | satisfied | `AR-397.4-20260904-b02630ba` | `7ed91dd404ba56da4115ae101b7e8c9f25d01484f67f55c5584adab484005296` | 2026-09-04 | known_installer.py:475-496 names superseded metadata identities; workforce.py:1033-1053 accepts them so divergence is None and reconcile re-projects from the current agent (1154-1165); test_known_contractor_install.py:380-424 asserts existing, no divergence, updated==1, current qualifiers. |
| 5 | satisfied | `AR-397.5-20260904-9b65ac3f` | `f260499d6df88b1aee4dc7f988cc3af363b03a2a1d310003f562b69f49d5aa3e` | 2026-09-04 | tests/test_operations_contractors.py:105-114 asserts the agent projects ['implementation','release'], confirmed by known_contractors.py:1080 and the installation-to-release map at known_installer.py:89-101,242; AR-397-evidence-20260904.txt:34-45 records the live store reading the same. |

## Builder notes

The two suites give 48 passed at the candidate. The five AR-397 tests and
the release-lifecycle test fail on `dda2c8a3^`, so the suite pins the change.

The live worker was installed at the current package, revision 0, so the live
store proves criteria 2 and 5 as installed state rather than as a transition;
the transition itself is the seeded-store test for criterion 2.

Decided with this close, recorded in the issue: the installer's per-slug
tables are part of a packaged identity, and the first change to one of them
for a shipped slug must pin the prior values beside the superseded contract.
