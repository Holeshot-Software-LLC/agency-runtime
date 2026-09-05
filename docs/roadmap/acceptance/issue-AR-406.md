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
candidate_commit: 12a62393613452fb322697b4cde48d8c74949422
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

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-406.1-20260905-84e8334e` | `8f8cd5492cf96212ed5390436dc30443200150336aff973dcaf1fcc4718dd71f` | 2026-09-05 | The cited Current coverage verification excerpt records the configured command exiting 0 with 138 tests passing and coverage of 96.92% lines, 86.62% branches, and 95.71% functions, exceeding all 95/86/93 floors. |
| 2 | satisfied | `AR-406.2-20260905-6cec4874` | `5fb1a59637269212cee49b2d229b79c85c8eec9293e2219c592c42a12188b008` | 2026-09-05 | scripts/run_local_gates.py and ci.yml use recursive dashboard JavaScript coverage with 95/86/93 floors; test_release_packaging.py enforces exact arguments for both gates, rejecting narrower scope and lower floors. |
| 3 | absent | `AR-406.3-20260905-9cd821a6` | `97f4bd94636867cbf0748f4eb553e77a47b5b1e9583169bc8dd21adc11f31513` | 2026-09-05 | The coverage report records 138 passing UI tests, and the excerpts show soak and teardown assertions, but ADR-0220 provides no baseline comparison or diff demonstrating unchanged production semantics and behavioral tests. |
