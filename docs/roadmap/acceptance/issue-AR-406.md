---
title: "AR-406 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, coverage]
related:
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-406
candidate_commit: d109b094be3bdefdff8a19998dc3566b24a0d93b
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/682
---

# AR-406 acceptance verification record

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | command-output | `Exact configured local command passes 138 cases and unchanged 95/86/93 floors over all seven product modules` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md#current-coverage-verification` |
| 2 | file | `Local command includes recursive production JavaScript scope and unchanged test invocation/floors` | 2026-09-05 | `scripts/run_local_gates.py:187-199` |
| 2 | file | `Hosted command uses the same recursive product scope and numeric floors` | 2026-09-05 | `.github/workflows/ci.yml:278-285` |
| 2 | test | `Both entry points have exact-argv regressions rejecting narrower patterns, exclusions or lower floors` | 2026-09-05 | `tests/test_release_packaging.py:320-344` |
| 2 | command-output | `Both regression cases first fail; the corrected complete workflow-contract package passes 163 cases` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md#command-contract-verification` |
| 3 | command-output | `All unchanged UI cases pass and all production modules remain measured` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md#current-coverage-verification` |
| 3 | test | `Unchanged fifty-render listener soak checks bounded listeners, correct worker selection and disposal` | 2026-09-05 | `tests/dashboard_ui.test.mjs:1262-1311` |
| 3 | test | `Unchanged lifecycle regression checks idempotent teardown, listener removal and pending-work cancellation` | 2026-09-05 | `tests/dashboard_ui.test.mjs:5777-5816` |
| 3 | file | `Decision explicitly changes measurement only and preserves every product module, test and numeric floor` | 2026-09-05 | `docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md#decision` |

| 3 | command-output | `Baseline and candidate have identical entire production-tree and UI-test Git objects; scoped diff exits zero` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-406-production-coverage-20260905.md#baseline-comparison` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-406.1-20260905-25b5ff67` | `b40d93b22facd4699673ad45faea6fac9384feeb076ae8602c322ed8c65e7d3f` | 2026-09-05 | The cited Current coverage verification records the exact configured command exiting 0 with 138 tests passing and coverage of 96.92% lines, 86.62% branches, and 95.71% functions, exceeding the existing 95/86/93 floors. |
| 2 | satisfied | `AR-406.2-20260905-e4f3e94c` | `7e819e28099425da77a2496c9398258f1f9b0e4bf24e78ee2b086075600bd55e` | 2026-09-05 | scripts/run_local_gates.py and .github/workflows/ci.yml use recursive dashboard JavaScript coverage with 95/86/93 floors; tests/test_release_packaging.py enforces exact arguments for both gates, rejecting narrower scope or lower floors. |
| 3 | satisfied | `AR-406.3-20260905-a884c123` | `eef4672a26cc23ef016b8e89aaff8b6f26fbb91fa4601aed1c1ec64257c32cb6` | 2026-09-05 | The coverage evidence records identical production-tree and UI-test Git objects and 138 passing UI tests; the cited listener soak and teardown excerpts verify listener bounds, disposal, and cancellation. |

## Prior verification

Commit d109b094 preserves the first two satisfied verdicts and the third absent
verdict with their exact reasons, run IDs and digests. The second candidate adds
the requested concrete baseline comparison; it changes no acceptance criterion,
production code or behavioral test. Re-freezing changes every evidence digest,
so all three criteria are verified again against the complete evidence packet.
