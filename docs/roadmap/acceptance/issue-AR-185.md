---
title: "AR-185 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, codex, activation]
related:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/decisions/0117-unify-owner-control-authority.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-185
candidate_commit: 500de0850deb7c18286caba64de3f45d276c54ce
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-185 acceptance verification record

## Builder evidence

This frozen packet contains observations only. The historical criterion-2/3
wording and their explicit existing-policy corrections are retained in the
receipt. No acceptance verdict is supplied here.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Exact parser-bound no-bypass verification form | 2026-09-07 | agency_runtime/core/codex_activation_verification.py:198-230 |
| 1 | file | One current-profile invocation with existing-current Store and no generic install | 2026-09-07 | agency_runtime/cli/install_commands.py:1439-1480 |
| 1 | test | Real CLI dispatch reaches one canary while generic dependencies are forbidden | 2026-09-07 | tests/test_codex_activation_verification.py:131-184 |
| 1 | command-output | Fresh CLI authority and parser focused package | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#cli-authority-and-parser-checks |
| 2 | file | Exact no-bypass key set, boolean fields and finite bounded timeout | 2026-09-07 | agency_runtime/core/codex_activation_verification.py:198-230 |
| 2 | file | Validation before dispatch and explicit distinct autonomous-mode branch | 2026-09-07 | agency_runtime/cli/install_commands.py:132-184 |
| 2 | file | Original wording and exact-slice reconciliation preserve separately supported trust modes | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#verification-scope-and-original-criterion-2 |
| 2 | test | Nearby and future public/private fields rejected by exact predicate | 2026-09-07 | tests/test_codex_activation_verification.py:189-234 |
| 2 | command-output | Fresh warning-strict boundary tests | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#cli-authority-and-parser-checks |
| 3 | file | Accepted owner CLI authority retains prepared mutation safeguards without presence ceremony | 2026-09-07 | docs/decisions/0117-unify-owner-control-authority.md:48-70 |
| 3 | file | Original wording and explicit owner-CLI correction | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#authority-reconciliation-and-original-criterion-3 |
| 3 | file | Prepared slice excludes verification and dispatches independently | 2026-09-07 | agency_runtime/core/prepared_codex_install.py:189-210 |
| 3 | file | Separate exact branch dispatch before generic work | 2026-09-07 | agency_runtime/cli/install_commands.py:1557-1580 |
| 3 | file | Preparation and repeated identity checks under the install lock precede publication | 2026-09-07 | agency_runtime/core/prepared_codex_install.py:1494-1537 |
| 3 | test | Verification predicate rejects prepared refresh shape | 2026-09-07 | tests/test_codex_activation_verification.py:260-265 |
| 4 | file | Special result returns before generic config loading or installation | 2026-09-07 | agency_runtime/cli/install_commands.py:1652-1668 |
| 4 | test | Controls, roster, contractors, dashboard and installer dependencies cannot be called | 2026-09-07 | tests/test_codex_activation_verification.py:110-184 |
| 4 | file | Restricted canary returns before catalog bootstrap or reconciliation | 2026-09-07 | agency_runtime/core/preflight.py:452-473 |
| 4 | file | Exact canary skips gap hiring after inference-owned routing | 2026-09-07 | agency_runtime/core/selector/pipeline.py:2213-2245 |
| 4 | test | Canary selection stays inference-owned and hiring is forbidden | 2026-09-07 | tests/test_activation_canary_contract.py:250-304 |
| 4 | command-output | Fresh inference-owned activation contract tests | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#inference-owned-activation-contract-checks |
| 5 | file | Coordinator requests existing-current Store before preparing invocation | 2026-09-07 | agency_runtime/core/canary_proof.py:387-421 |
| 5 | file | Configured-path, trusted-parent, schema and WAL checks without initialization | 2026-09-07 | agency_runtime/core/store/sqlite.py:929-950 |
| 5 | file | Existing-only SQLite open and identity revalidation prevent race-created replacement | 2026-09-07 | agency_runtime/core/store/sqlite.py:1333-1365 |
| 5 | file | Spawned hook consumes the restricted existing-current requirement | 2026-09-07 | agency_runtime/adapters/hooks.py:3641-3651 |
| 5 | test | Existing-current mode refuses bootstrap and permission repair | 2026-09-07 | tests/test_codex_activation_verification.py:421-468 |
| 5 | test | Existing-Store requirement crosses actual process-runner boundary | 2026-09-07 | tests/test_codex_activation_verification.py:579-605 |
| 5 | command-output | Fresh Store, canary and identity-boundary checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#store-and-canary-checks |
| 6 | file | Fresh invocation time, profile, proof, trace and installation identity binding | 2026-09-07 | agency_runtime/cli/install_commands.py:1203-1262 |
| 6 | file | Final inventory must expose the same fresh attestation with trusted hooks | 2026-09-07 | agency_runtime/cli/install_commands.py:1265-1286 |
| 6 | test | Malformed fresh reports cannot borrow existing proof | 2026-09-07 | tests/test_codex_activation_verification.py:265-309 |
| 6 | test | Wrong final trace and correctly-shaped old reports are rejected | 2026-09-07 | tests/test_codex_activation_verification.py:312-374 |
| 6 | command-output | Concrete installed v4 proof and native child correlation | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#existing-installed-live-proof |
| 7 | file | Canary errors still lead to final inspection before completeness decision | 2026-09-07 | agency_runtime/cli/install_commands.py:1467-1508 |
| 7 | file | Closed report projection retains only bounded named fields | 2026-09-07 | agency_runtime/cli/install_commands.py:1289-1342 |
| 7 | file | Incomplete verification returns nonzero after bounded output | 2026-09-07 | agency_runtime/cli/install_commands.py:1550-1554 |
| 7 | test | Failed initial inspection does not invoke canary and exceptions do not expose private text | 2026-09-07 | tests/test_codex_activation_verification.py:377-418 |
| 7 | test | Unknown or malformed result content does not survive the projection | 2026-09-07 | tests/test_codex_activation_verification.py:471-577 |
| 7 | command-output | Fresh CLI boundary tests include malformed and exception paths | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#cli-authority-and-parser-checks |
| 8 | command-output | Authority, verification, installer and parser package: 175 passed | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#cli-authority-and-parser-checks |
| 8 | command-output | Store and canary package: 71 passed, 40 Windows cases deselected | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#store-and-canary-checks |
| 8 | command-output | Inference-owned activation contract package: 28 passed | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#inference-owned-activation-contract-checks |
| 9 | command-output | Installed current-profile no-bypass v4 success, v6 delivery and precise native-trust limits | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#existing-installed-live-proof |
| 9 | command-output | All 328 installed modules match pinned runtime; verification path matches current source, not whole main | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md#installed-source-identity |
| 9 | file | Exact no-bypass current-profile inventory admission precedes the native invocation | 2026-09-07 | agency_runtime/core/canary_backends.py:3571-3629 |
| 9 | command-output | Existing receipt re-verification of host-written card before speech | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md#independent-read-only-correlation |

## Verification

All nine isolated checks returned satisfied. Criterion 4 required one bounded
retry after an unavailable result; the earlier absence is retained in the
receipt and Git history. No builder supplied these verdicts.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-185.1-20260907-0aeefa58` | `a88a3aaab543db74b88fde19c6cf9e865ccbf91c3d036111d5585cf41079e824` | 2026-09-07 | install_commands.py:1658-1696 returns from the verification dispatch before detect_installed_agents is imported or called, and 1473-1481 issues exactly one current-profile canary; test_codex_activation_verification.py:131-191 runs the documented CLI form with that verifier forbidden. |
| 2 | satisfied | `AR-185.2-20260907-e93954ce` | `2e862caea2002753d7dedb38c031166517242bdd939ec269fb14131a112dadbf` | 2026-09-07 | Snapshot shows codex_activation_verification.py:198-230 exact key-set and bounded timeout checks, install_commands.py:132-184 validating before dispatch at cmd_install:1658-1666, and tests at test_codex_activation_verification.py:198-263 rejecting neighbor shapes, extra fields, 0/601/nan timeouts. |
| 3 | satisfied | `AR-185.3-20260907-7a5d3d50` | `eb1a42749460be6ba95c358143a7b12cf22fb7fb3a15d791011b29f529a8a730` | 2026-09-07 | prepared_codex_install.py:189-210 requires verify_activation False and no_dashboard True, inverse of codex_activation_verification.py:198-230; install_commands.py:1557-1580 dispatches separate owner-CLI branches; refresh:1494-1537 keeps locked re-prepare safeguards; test:260-263 asserts non-overlap. |
| 5 | satisfied | `AR-185.5-20260907-aecc83bb` | `03c936b3f1706d6a9950d7460c0821b1f48e5588eb8febd213828820ff5b615d` | 2026-09-07 | sqlite.py:930-950 requires exact configured path, trusted parent, current schema and WAL, returning before initialization; repair is gated and _connect uses mode=rw with identity recheck; coordinator (canary_proof.py:409, install_commands.py:1480) and hook (hooks.py:3645-3651) set it; tests exist. |
| 6 | satisfied | `AR-185.6-20260907-ce5ec439` | `1491ab92f1aa3d5b764591aeff34586017df9b55e57157868ec2009372db5fc5` | 2026-09-07 | install_commands.py:1203-1262 requires a current-profile persisted attestation sampled within this invocation's window, bound to identity, and rejects reuse of prior proof_digest/trace_id; 1265-1286 with caller 1489-1508 demands exact final-inventory match; tests 265-374 confirm stale rejection. |
| 7 | satisfied | `AR-185.7-20260907-2cbbfc06` | `1acf1651fb57267675246e4a5fd3e0c7d7a4ad6dc42966d8a45d8fec36fdc42a` | 2026-09-07 | install_commands.py:1472-1508 catches canary exceptions then always re-inspects before deciding, returning 1 at line 1554; the projection (1289-1342) and _bounded_unmet_prerequisites (1152-1181) keep only bounded named fields, per tests test_codex_activation_verification.py:398-418, 471-577. |
| 8 | satisfied | `AR-185.8-20260907-d5b6cbbf` | `f440d2df8ac7d63f692b740132f8287368cef36c78f16aedf229da1103fda053` | 2026-09-07 | Evidence doc lines 165-206 in the snapshot record three pytest runs with -W error, exit zero, 175/71/28 passed; all eight cited modules covering authority, canary, Store, parser and installer exist at the candidate commit, and parametrize plus windows markers explain counts and deselections. |
| 9 | satisfied | `AR-185.9-20260907-24d54ce6` | `884e63715c6e4afdb2db5ad3d920704e51e284205dbc3ccfd235cf9c07e0a124` | 2026-09-07 | AR-404 records the installed CLI live report: canary_passed and complete true, attestation persisted, installation_attempted and trust_bypass_used false, current-profile v4 digest; snapshot canary_backends.py:3571-3641 and install_commands.py:1265-1286 require trusted hook inventory first. |
| 4 | satisfied | `AR-185.4-20260907-61c45536` | `4f528999e36dd5dc1596d4fc43701adee095e98e761eca97f288a47566eb27e4` | 2026-09-07 | Snapshot shows install_commands.py:1660 returning before _load_install_config, the verify branch using only inspector/canary_runner; preflight.py:467 skips roster/contractor/catalog work, pipeline.py:2225 skips gap hiring, and the cited tests forbid config, Store, controls, dashboard, adapter calls. |
