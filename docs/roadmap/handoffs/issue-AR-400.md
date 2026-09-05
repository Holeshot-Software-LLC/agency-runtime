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
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-400
branch: codex/ar400-staffing-contracts
evidence_commit: 47ab9fcebc1fe8106e7f776710db85e4be8c3e54
minimum_ledger_commit: 556e0ebf361c09dc4ed1271f574bee0eba12ef57
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/665
---

# AR-400 staffing correctness and performance delivery

## Checkpoint

Owner requested self-implementation, PR merge to main, agency install and smoke
tests of all five harnesses; then added a performance pass preserving quality.
No delegation. Branch includes the refreshed previously unpushed AR-383 capsule.
Metadata names that clean starting point; this recovery commit carries code
changes and its following ledger identifies it. Phase: fast_verification.

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
- AR-403 #668 implements fresh-process cache reuse, no query persistence,
  lossless vectors, one-hour TTL, model/roster invalidation and private paths.
- Targeted transport/deadline/cache/domain/hiring suites: 145 passed.
- Preflight, receipt and conformance-manifest suites: 94 passed, one skipped.
- JS: 138 passed. Routing evaluation passed. Ruff check/format now clean.
- Fast spine: 1003 passed, three skipped, one stale domain-mutation anchor failed.
  Anchor now tests that the superseded domain veto cannot return; focused
  manifest check passes. Full fast spine rerun remains due.

## Exact blocker

No implementation blocker. Fast-spine rerun, live timing, acceptance records,
merge, install and live proof remain. Reinstallation
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

1. Run decision-conformance in the copied-interpreter dev venv with umask 077.
   Ambient umask 0002 made the runner's scratch parents group-writable; the
   initial system-python run also lacked pytest under the isolated home.
2. Measure cold versus warm roster embeddings in fresh processes.
3. Run named fast spine, JS, routing, docs and decision-conformance.
4. Record acceptance, merge through a PR and install from main.
5. Deterministic smoke all five hosts; bounded live canaries/ordinary turns where
   supported. Record trust/platform blockers without unattended retry loops.

## Verification

Checks above use real verification/hiring functions, scripted replies and
temporary stores. No live provider call or live roster mutation by these tests.
No exhaustive corpus, coverage or compatibility matrix was run. Baseline
lint/format defects were mechanically corrected, the field-shadow and mutable
test-fixture errors fixed, and deadline complexity factored without suppressions.
Actual-preflight regression confirms terminal closure and explicit Store cache
scope even while durable writes are deferred.

## Constraints

Self-implementation; no subagents. Branch/worktree and PR, never commit to main.
Each substantive commit gets its immediately following worklog ledger.
No secret printing, new keys, provider reconfiguration or native trust bypass.
Do not weaken critics or authority for speed. Preserve historical evidence and
do not close unrelated trackers.
