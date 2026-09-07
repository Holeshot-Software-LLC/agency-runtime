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

No verifier has judged these rows yet.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
