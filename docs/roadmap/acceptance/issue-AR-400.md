---
title: "AR-400 acceptance verification record"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, verification, staffing, installation]
related:
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/handoffs/issue-AR-400.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-400
candidate_commit: 87159dc075f28747beae640a927f709188b53f02
evidence_cutoff: 2026-09-05
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/665
---

# AR-400 acceptance verification record

Candidate includes the merged code and the repository-local installed report.
The builder supplies evidence only; operator/platform blockers are not live passes.

## Builder evidence

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | test | `Six composed real-hiring cases cover one/two gaps, direct/deferred commits and per-turn caps retaining the first assignment` | 2026-09-05 | `tests/test_staffing_contract_boundaries.py:103-164` |
| 1 | test | `Gap setup uses valid inferred empty rankings and a separately nominated reviewer, then the real verifier` | 2026-09-05 | `tests/test_staffing_contract_boundaries.py:29-100` |
| 2 | test | `Amending the worker on one unit retains the same worker's other nominated unit and passes full re-verification` | 2026-09-05 | `tests/test_staffing_contract_boundaries.py:167-226` |
| 2 | file | `restaff_after_hire rebuilds the complete proposal and calls verify_staffing on the full plan, proposal and current contracts before accepting` | 2026-09-05 | `agency_runtime/core/workforce/hiring.py:2715-2830` |
| 3 | command-output | `Exact main PR/commit, immutable install, dashboard, deterministic all-host checks and native install outcomes` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-400-installed-delivery-20260905.md:20-64` |
| 3 | command-output | `Claude live native-child proof, Codex trust refusal and explicit Hermes/OpenClaw/ZCode operator/platform blockers; no all-live claim` | 2026-09-05 | `docs/roadmap/acceptance/evidence/AR-400-installed-delivery-20260905.md:53-107` |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-400.1-20260905-f5378d28` | `36692970f1c442d3c373bf8a92b3588ae288e9cf1c21dc79afb754d2b48c9fca` | 2026-09-05 | tests/test_staffing_contract_boundaries.py:29-164 covers one and two empty gaps in both commit modes, asserts retained assignments, and identifies the remaining gap with task_hiring_limit_reached when capped. |
| 3 | satisfied | `AR-400.3-20260905-647dc189` | `02a805a13c3253b14eb3587b9370f28fe7f6c391453cf8caa19fd8978c70f0ac` | 2026-09-05 | AR-400-installed-delivery-20260905.md:20-107 records PR #669 and main merge, the exact installed VCS package, passing deterministic smoke for all five harnesses, and a live attempt or explicit operator/platform blocker for each. |

## Builder notes

The first isolated verdict for criterion 2 was absent because its production
wiring was not included in the excerpts. Commit 606065f2 preserves that judgment.
The builder now cites the actual call sites; the changed evidence awaits a fresh
verifier judgment and does not inherit the old digest.

The installed build is 1de05aea from PR #669, not the later documentation-only
candidate. OpenClaw did not update because restart consent is outstanding.
Codex hooks are present but need attended trust. These are explicit blockers,
not waived gates or fabricated canary results.
