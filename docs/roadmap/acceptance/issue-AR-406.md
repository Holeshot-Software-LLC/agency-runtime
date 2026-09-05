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

## Prior verification

Commit d109b094 preserves the first two satisfied verdicts and the third absent
verdict with their exact reasons, run IDs and digests. The second candidate adds
the requested concrete baseline comparison; it changes no acceptance criterion,
production code or behavioral test. Re-freezing changes every evidence digest,
so all three criteria are verified again against the complete evidence packet.
