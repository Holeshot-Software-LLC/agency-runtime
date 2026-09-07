---
title: "AR-176 acceptance verification record"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, verification, testing, security]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0224-retire-duplicate-mandatory-coverage-checklist.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-176
candidate_commit: 8b4c1fca2205e3132133e6ecc4c4ef62238bc653
evidence_cutoff: 2026-09-07
tracker_url: null
---

# AR-176 acceptance verification record

## Builder evidence

Current scope is test-contract reconciliation, not a new aggregate or all-host
activation claim. July's exact reported results and original criteria remain
historical. No verifier verdict is supplied by the builder.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | Suite isolation opts out only for explicit configuration identity | 2026-09-07 | tests/conftest.py:173-213 |
| 1 | test | OpenClaw preserves a space-bearing explicit configuration path | 2026-09-07 | tests/test_adapter_parity.py:1412-1458 |
| 1 | test | Dashboard install fixture retains configured Store authority | 2026-09-07 | tests/test_dashboard_service_coverage_complete_operations.py:358-400 |
| 1 | command-output | Affected modules pass together | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:563-584 |
| 2 | test | Prepared argv keeps security keywords and revalidates immediately before spawn | 2026-09-07 | tests/test_executable_namespace_security.py:578-661 |
| 2 | command-output | Current affected-module package executes those security contracts | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:563-584 |
| 3 | test | Strict path fixture materializes the actual resolved file | 2026-09-07 | tests/test_owned_process_core_hardening.py:362-382 |
| 3 | test | Candidate and snapshot rows carry immutable event IDs | 2026-09-07 | tests/test_roster_authority_gap_coverage_ar91.py:37-81 |
| 3 | test | Real Store materializes quarantined candidate and approved activated snapshots | 2026-09-07 | tests/test_roster_activation_authority.py:128-149 |
| 3 | test | Complete immutable authority permits real revision rollback | 2026-09-07 | tests/test_roster_activation_authority.py:905-936 |
| 3 | command-output | Materialized authority and path modules pass in the combined process | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:563-584 |
| 4 | file | Distinct missing and non-runnable Node failures retain frozen launch checks | 2026-09-07 | agency_runtime/core/smoke.py:250-285 |
| 4 | test | Missing Node keeps static validation | 2026-09-07 | tests/test_doctor.py:361-378 |
| 4 | test | Non-runnable Node and invalid-script results stay distinct | 2026-09-07 | tests/test_smoke_coverage_complete.py:83-109 |
| 4 | command-output | Node smoke contracts pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:490-503 |
| 4 | command-output | Doctor module passes in current combined package | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:563-584 |
| 5 | file | Exact faithful July repair and eleven-case report | 2026-09-07 | docs/worklog/2026-07-27-b520fa7-full-gate-contracts.md:24-69 |
| 5 | file | Dated subsequent complete-corpus history remains visible | 2026-09-07 | docs/analysis/2026-07-26-production-readiness-review.md:305-327 |
| 5 | command-output | Every affected test module passes together; no fabricated original node list | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:563-584 |
| 5 | file | Current report explicitly separates unrecoverable node list and historical aggregate | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:476-489 |
| 6 | command-output | One warning-strict ordered process, exact module list and platform exclusions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:563-584 |
| 7 | test | Removed delegate cannot fabricate evidence; native event replay deduplicates | 2026-09-07 | tests/test_turn_scoped_evidence.py:295-344 |
| 7 | test | Both hosts terminalize the first invalid response without corrections | 2026-09-07 | tests/test_turn_scoped_evidence.py:374-429 |
| 7 | test | Synthetic ACL double uses actual boundary while permission chains stay checked | 2026-09-07 | tests/test_storage_parent_trust.py:141-218 |
| 7 | test | File write/owner/link/inode guards and real ACL denial stay intact | 2026-09-07 | tests/test_storage_parent_trust.py:335-400 |
| 7 | test | Failed inference preserves operator prompt and creates neither fallback nor turn | 2026-09-07 | tests/test_public_api.py:340-383 |
| 7 | test | Cleanup double performs guarded removal and checks both paths absent | 2026-09-07 | tests/test_coverage_final_delegation_private.py:168-210 |
| 7 | command-output | Exact six original failure names and red result | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:282-291 |
| 7 | command-output | Both baseline failure classes and seven-case green run | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:353-398 |
| 8 | file | Bounded delivery replaces unrequested exhaustive gates | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md:62-84 |
| 8 | file | Diagnostic failures remain owned without waiving optional coverage floor | 2026-09-07 | docs/decisions/0224-retire-duplicate-mandatory-coverage-checklist.md:44-65 |
| 8 | command-output | Current combined and focused checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:368-420 |
| 8 | command-output | Current named fast production spine | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:585-614 |
| 8 | command-output | Current complete UI and unchanged coverage floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:437-475 |
| 8 | command-output | Strict metadata policy worklog documentation tracker Ruff and diff | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:615-630 |
| 8 | command-output | Actual Codex refresh and activation failure, no asserted injection | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md:24-87 |
| 8 | command-output | Actual Claude invocation parses header but fails staffed delivery | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md:132-186 |

## Verification

First verdicts are preserved at 969f7190. Source assertions were strengthened,
full Store authority evidence replaces a cache-isolation citation, and the six
original failure names are explicitly included. All eight criteria are to be
checked anew at this final candidate; no first-pass verdict is copied.

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
