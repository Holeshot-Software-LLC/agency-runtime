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
branch: codex/ar400-delivery
evidence_commit: 1de05aead322dbbf359a0a5f3ab19dcbb7cdeff9
minimum_ledger_commit: df1ace064a67eff357d7f364fdb4cfc805207154
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/665
---

# AR-400 staffing correctness and performance delivery

## Checkpoint

Owner requested self-implementation, PR merge to main, agency install and smoke
tests of all five harnesses; then added a performance pass preserving quality.
No implementation delegation. PR #669 merged the fixes and refreshed AR-383
capsule to main at 1de05aea. Phase: done for the bounded four-issue review.
This delivery branch records installed proof and isolated acceptance. The
worklog registry identifies the delivery PR merge without changing runtime.

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
- Fast spine rerun: 1004 passed, three skipped.
- Decision-conformance: baseline passed; all 182 mutations killed, zero invalid
  or surviving; source unchanged at the recorded run.
- Two fresh-process live recall observations: cold 63.620 s (49.759 embedding,
  283 inputs), warm 8.804 s (2.804 embedding, one input, cache hit).
  Evidence: docs/roadmap/acceptance/evidence/AR-403-recall-performance-20260905.json.
  Fifteen of sixteen additions overlap; reranked lists differ. This proves
  reduced embedding work, not total staffing latency or live quality equivalence.
- Focused review adds a last CLI launch-time deadline check and propagates an
  explicit direct-hiring deadline into its transport context.
  Follow-up deadline/CLI/hiring/credential/conformance suites: 135 passed.

## Exact blocker

All twelve isolated acceptance criteria for AR-400 through AR-403 are now
satisfied. Latest focused regression: 228 passed, one skipped. The bounded
review package is done at this checkpoint; the broader
native rollout below remains waiting_for_operator, not an all-live pass.

Runtime installed from non-editable commit-pinned venv 1de05aea; projection
349f1ae7fc74. Dashboard restarted and is reachable. PATH launcher updated with
its old launcher backed up. All-host deterministic smoke: eight checks passed,
zero failures/skips, five host parity cases passed. Claude isolated live canary
passed at 16:51Z: code-reviewer delivered, runtime hash matched, header valid.
No persistent current-profile attestation is claimed by that isolated proof.
Codex activation attempt stopped before model invocation: eight hooks modified,
zero trusted. Owner must review them in a fresh terminal TUI. OpenClaw install
waits for permission to stop/restart its live gateway. Hermes and ZCode have no
proven bounded native-child noninteractive canary; ZCode has no discovered CLI.

## Same-task continuity

Continue on the delivery branch; shared main is clean at 1de05aea. Later
documentation-only merges need not replace the identical installed payload.
The owner added backlog cleanup/completion: audit found 155 unfinished records
(56 open, 99 in_progress), 153 without acceptance records before this package.
Do not equate old implementation notes with acceptance or mass-close the queue.

## Next bounded work package

1. Continue the committed AR-404 backlog plan; 151 baseline items remain after
   this four-issue package. AR-397/398/399 tracker bookkeeping is reconciled.
2. Reproduce and implement AR-348/349 with fallback, harness and atomicity
   coverage; the current replay proves strict independence is still ineffective.
3. Complete native operator steps only when available. Never retry a trust or
   restart-consent blocker unattended; do not call the entire backlog done.

## Verification

Checks above use real verification/hiring functions, scripted replies and
temporary stores. No live provider call or live roster mutation by these tests.
No exhaustive corpus, coverage or compatibility matrix was run. Baseline
lint/format defects were mechanically corrected, the field-shadow and mutable
test-fixture errors fixed, and deadline complexity factored without suppressions.
Actual-preflight regression confirms terminal closure and explicit Store cache
scope even while durable writes are deferred.
Tracker checks identified missing remote AR-398/AR-399 and stale-open AR-397.
The owner's subsequent backlog-cleanup request includes reconciling this record
debt after checking existing acceptance. AR-400 through AR-403 are linked.

## Constraints

Self-implementation; no subagents. Branch/worktree and PR, never commit to main.
Each substantive commit gets its immediately following worklog ledger.
No secret printing, new keys, provider reconfiguration or native trust bypass.
Do not weaken critics or authority for speed. Preserve historical evidence and
do not close items without applicable acceptance evidence.
