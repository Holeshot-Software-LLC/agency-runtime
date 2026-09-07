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
candidate_commit: 49b307ff3ae7d248bee0b7135d5b0843daa9b1de
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
| 1 | command-output | Affected modules pass together | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:399-420 |
| 2 | test | Prepared argv keeps security keywords and revalidates immediately before spawn | 2026-09-07 | tests/test_executable_namespace_security.py:578-642 |
| 2 | command-output | Current affected-module package executes those security contracts | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:399-420 |
| 3 | test | Strict path fixture materializes the actual resolved file | 2026-09-07 | tests/test_owned_process_core_hardening.py:362-382 |
| 3 | test | Candidate and snapshot rows carry immutable event IDs | 2026-09-07 | tests/test_roster_authority_gap_coverage_ar91.py:37-81 |
| 3 | test | Remediation cursor models iteration, current basis and queue cache rows | 2026-09-07 | tests/test_roster_sync_gap_coverage_child.py:1377-1446 |
| 3 | command-output | Materialized authority and path modules pass in the combined process | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:399-420 |
| 4 | file | Distinct missing and non-runnable Node failures retain frozen launch checks | 2026-09-07 | agency_runtime/core/smoke.py:250-285 |
| 4 | test | Missing Node keeps static validation | 2026-09-07 | tests/test_doctor.py:361-378 |
| 4 | test | Non-runnable Node and invalid-script results stay distinct | 2026-09-07 | tests/test_smoke_coverage_complete.py:83-109 |
| 4 | command-output | Node smoke contracts pass | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:490-503 |
| 4 | command-output | Doctor module passes in current combined package | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:399-420 |
| 5 | file | Exact faithful July repair and eleven-case report | 2026-09-07 | docs/worklog/2026-07-27-b520fa7-full-gate-contracts.md:24-69 |
| 5 | file | Dated subsequent complete-corpus history remains visible | 2026-09-07 | docs/analysis/2026-07-26-production-readiness-review.md:305-327 |
| 5 | command-output | Every affected test module passes together; no fabricated original node list | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:399-420 |
| 5 | file | Current report explicitly separates unrecoverable node list and historical aggregate | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:476-489 |
| 6 | command-output | One warning-strict ordered process, exact module list and platform exclusions | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:399-420 |
| 7 | test | Removed delegate cannot fabricate evidence; native event replay deduplicates | 2026-09-07 | tests/test_turn_scoped_evidence.py:295-344 |
| 7 | test | Both hosts terminalize the first invalid response without corrections | 2026-09-07 | tests/test_turn_scoped_evidence.py:374-429 |
| 7 | test | Synthetic ACL double uses actual boundary while permission chains stay checked | 2026-09-07 | tests/test_storage_parent_trust.py:141-218 |
| 7 | test | File write/owner/link/inode guards and real ACL denial stay intact | 2026-09-07 | tests/test_storage_parent_trust.py:335-400 |
| 7 | test | Failed inference preserves operator prompt and creates neither fallback nor turn | 2026-09-07 | tests/test_public_api.py:340-383 |
| 7 | test | Cleanup double performs guarded removal and checks both paths absent | 2026-09-07 | tests/test_coverage_final_delegation_private.py:168-210 |
| 7 | command-output | Both baseline failure classes and seven-case green run | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:353-398 |
| 8 | file | Bounded delivery replaces unrequested exhaustive gates | 2026-09-07 | docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md:62-84 |
| 8 | file | Diagnostic failures remain owned without waiving optional coverage floor | 2026-09-07 | docs/decisions/0224-retire-duplicate-mandatory-coverage-checklist.md:44-65 |
| 8 | command-output | Current combined and focused checks | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:368-420 |
| 8 | command-output | Current named fast production spine | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:421-436 |
| 8 | command-output | Current complete UI and unchanged coverage floors | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:437-475 |
| 8 | command-output | Strict metadata policy worklog documentation tracker Ruff and diff | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md:504-532 |
| 8 | command-output | Actual Codex refresh and activation failure, no asserted injection | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md:24-87 |
| 8 | command-output | Actual Claude invocation parses header but fails staffed delivery | 2026-09-07 | docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md:132-186 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-176.1-20260907-8f9667dd` | `214186b6d30dfbe8c4a5faf7f7fa8e87a8fb5fcf6d1407ec6bfd411b50a66e0c` | 2026-09-07 | tests/conftest.py:173-213 removes AGENCY_DB_PATH for configuration-identity tests; the marked OpenClaw test asserts the explicit configuration's database path, and the cited combined run reports 467 passed. |
| 2 | absent | `AR-176.2-20260907-62a21f1f` | `52d9bfe89e75ae219b0718669bc5e91b0c2caf39123264cc38eded76f9b6030a` | 2026-09-07 | The cited tests accept but discard **_kwargs without checking executable namespace or forbidden-root arguments; the recorded passing suite does not demonstrate that test doubles retain them. |
| 3 | contradicted | `AR-176.3-20260907-233b1a2a` | `7554341cbe152d5d559a5a01f44baa3fc0ae6b3be86716ae478c78aed919f26c` | 2026-09-07 | tests/test_roster_sync_gap_coverage_child.py:1377-1446 bypasses authority checks and queue validation with monkeypatched lambdas, despite the materialized path and event IDs shown in the other fixtures. |
| 4 | satisfied | `AR-176.4-20260907-2222f57b` | `a0fada62bfe5a66edc5d2183b24506dec84bead82e343f33fbdcad6aff157a03` | 2026-09-07 | smoke.py:250-285 preserves distinct missing and non-runnable Node diagnostics with argv freezing and immediate revalidation; the cited tests and passing command outputs confirm both diagnostic paths. |
| 5 | satisfied | `AR-176.5-20260907-298cf31a` | `7d8d0580f6fe787a2666bd988a784de813433f23628d7ed051da3e1ec22ebc2b` | 2026-09-07 | The July worklog preserves the eleven-failure repair and exact results, the production review retains subsequent history, and AR-176 evidence records the combined affected-module run with 467 passed, 1 skipped, and 64 deselected. |
| 6 | satisfied | `AR-176.6-20260907-a2a7a5e2` | `ca7936b91cb66de714c40c0c2880dd848d0ab2ca741e74fe61695a354b3f34f9` | 2026-09-07 | The cited evidence at lines 399-420 lists 14 current and neighboring modules in one ordered pytest command with -W error, explicitly excludes Windows tests, and reports 467 passed, 1 skipped, and 64 deselected. |
| 7 | absent | `AR-176.7-20260907-88cb7ccf` | `b10fc787b742984e77a905a3e642118906bf63574535d2bcb1f0aff6d372a906` | 2026-09-07 | The test excerpts and AR-176-fixture-contracts-20260907.md show seven passing cases and preserved safeguards, but the supplied evidence records only the cleanup failure, not the six carried stale failures. |
| 8 | satisfied | `AR-176.8-20260907-1e4adf27` | `7c08463a716403d020ae497f39c3bcee15db764d4f0868ce663294a9dc006538` | 2026-09-07 | AR-176 evidence records passing focused, fast-spine, UI-floor and strict checks, distinguishes historical runs, and ADRs 0105/0224 preserve optional controls; AR-404 separately reports failed live activation and unproven injection. |
