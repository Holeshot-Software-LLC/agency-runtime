---
title: "AR-400 staffing correctness and performance delivery"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, staffing, performance, installation]
related:
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-400
branch: codex/ar400-staffing-contracts
evidence_commit: cbbd2cff58eec66b680ddd608d85c4ec4d296aa3
minimum_ledger_commit: cbbd2cff58eec66b680ddd608d85c4ec4d296aa3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/665
---

# AR-400 staffing correctness and performance delivery

## Checkpoint

Owner requested self-implementation, PR merge to main, agency install and smoke
tests of all five harnesses; then added a performance pass preserving quality.
No delegation. Branch includes the refreshed previously unpushed AR-383 capsule.
Metadata names that clean starting point; this recovery commit carries code
changes and its following ledger identifies it. Phase: focused_review.

## Completed evidence

- Empty-gap tests first failed four cases with one-gap controls passing; all six
  direct/deferred/capped cases now pass. Amendment restaffing preserves other units.
- A simulated 75-second lease now calls with timeouts 60 and 15, stops at elapsed
  65, names exhaustion and commits no incomplete pending worker.
- New boundary suites: 25 passed, including five host identities.
- Hiring, coverage-gap and shortfall suites: 104 passed.
- Planner-domain, selection-safety and workforce-inference suites: 130 passed,
  one skipped.
- Domains no longer veto eligibility or require extra teammates; audited
  authority, explicit exclusions and actual capabilities remain enforced.
- Trackers: AR-400 #665, AR-401 #666, AR-402 #667.

## Exact blocker

No implementation blocker. Transport/preflight integration coverage, full fast
spine, acceptance records, merge, install and live proof remain. Reinstallation
requires native Codex trust; never fabricate hashes. The parent lacks the gateway
key; existing documented common.env loading is the live-test path, without new
keys or printing secrets.

## Same-task continuity

Continue on this branch; main remains e6531004. Preserve 45b51a20/cbbd2cff.
Performance lead: the supplied September 2–5 failure snapshot has 11 timed
embedding attempts, median 40.44 s, versus planner 50 samples median 8.37 s and
recruiter 15 samples median 14.79 s. Small failure-biased samples, not a current
benchmark. hybrid_recall.py caches roster vectors only inside one process while
hooks start fresh processes. Verify fresh-process reuse before claiming speedup.

## Next bounded work package

1. Finish transport/actual-preflight deadline regressions and focused review.
2. Measure cold versus warm roster embeddings in fresh processes; implement
   bounded identity-bound reuse if privacy and quality are preserved.
3. Run named fast spine, JS, routing, docs and decision-conformance.
4. Record acceptance, merge through a PR and install from main.
5. Deterministic smoke all five hosts; bounded live canaries/ordinary turns where
   supported. Record trust/platform blockers without unattended retry loops.

## Verification

Checks above use real verification/hiring functions, scripted replies and
temporary stores. No live provider call or live roster mutation by these tests.
Fast spine and exhaustive integration gates not yet run this turn. The original
review found baseline lint/format failures; distinguish those from new findings.
Current deadline seams add complexity warnings in inference and structured
transport; factor those during focused review before the merge gate.

## Constraints

Self-implementation; no subagents. Branch/worktree and PR, never commit to main.
Each substantive commit gets its immediately following worklog ledger.
No secret printing, new keys, provider reconfiguration or native trust bypass.
Do not weaken critics or authority for speed. Preserve historical evidence and
do not close unrelated trackers.
