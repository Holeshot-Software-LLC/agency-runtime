---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [handoff, routing, workforce, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/worklog/2026-07-23-ar119-installed-release-instrumented-recovery.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-115-live-routing-trust
evidence_commit: a6007afc713a5eadb4b1cbbc753f93f747457591
minimum_ledger_commit: a8822d774fd05f4ca538fc07241e7399c84191fb
hard_checkpoint_percent: 50
live_evaluation_admission_percent: 65
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

This is the bounded bootstrap projection for the next AR-119 package. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) remains the
complete historical and acceptance contract.

## Checkpoint

- Branch: codex/ar-115-live-routing-trust.
- Substantive evidence commit:
  a6007afc713a5eadb4b1cbbc753f93f747457591.
- Minimum ledger commit:
  a8822d774fd05f4ca538fc07241e7399c84191fb.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  which remains open.
- The current HEAD may be newer than the minimum ledger commit but must contain
  it.

## Completed evidence

- The required unchanged complete 19-case Windows corpus ran from clean ledger
  checkpoint 8622b0b after telemetry admitted it at 72.2% remaining. Both raw
  streams were captured outside the repository before parsing.
- The process returned status 1 in 422.492054 seconds. Its 1,179,731-byte
  stdout had SHA-256
  cd3b36733b56b4c631da9ffea259fa278c597438ecbe59e3275f3e1d25e687d0;
  stderr was empty. Independent byte-count and hash verification matched the
  atomic manifest. The exact 13,055-byte projection had SHA-256
  c835cc1ea1a9fa6cc22a31d847f1beb30b1ecc7f9e4ecbfb5b23ba858598cb5d.
- All 38 arms retained the unchanged corpus, roster, allowed-agent, provider,
  requested/actual model, explicit-model receipt, one-call, applied-inference,
  and 15000 ms bindings.
- Agency passed 17/19 with precision 0.880000, recall 0.758621, F1 0.814815,
  17/19 typed coverage, p50 8152.614 ms, p95/max 13452.227 ms, complete
  required disabled disclosure, and zero forbidden, ineligible, or conflict
  selections.
- Application observability and the broad application safely abstained on
  selection confidence at 10053.488 ms and 13452.227 ms. Installed release,
  active incident, and clinical/legal all passed in this corpus.
- Descriptive upstream passed 6/19 with precision 0.731707, recall 0.517241,
  F1 0.606061, 8/19 typed coverage, p50 13035.438 ms, and p95/max
  25231.637 ms. Three arms returned unknown disabled shadows and one returned
  an invalid assignment row, so the benchmark is invalid and none is an
  upstream loss.
- No general defect was established and no product, policy, parser, worker-
  contract, coverage, latency, or call-budget rule changed.

## Exact blocker

- Complete Agency corpora have varied from 19/19 to 18/19 and multiple 17/19
  observations. The newest failures are two different safe confidence
  abstentions after the previously failing installed-release case recovered.
- No complete corpus has produced 19 benchmark-valid upstream arms. Malformed,
  no-response, or timed-out arms remain validity failures, never comparative
  losses.
- Immediately after the corpus, telemetry was 55.7%, below the fixed 65% live-
  work gate. The conditional instrumented two-case confirmation therefore
  remains unstarted in this same task.

## Same-task continuity

- Context thresholds do not create, fork, dispatch, or wait for another task.
- Continue this package in the current task through normal Codex compaction.
- Below 65 percent remaining, no new expensive live evaluation may start. At
  or below 50 percent, first preserve a clean durable checkpoint, then continue
  in the same task.

## Next bounded work package

Stay in matched selection; do not advance to contractor lifecycle. Run one
instrumented matched confirmation of `application-observability` and
`broad-python-typescript-application`. A pass-through `agency_router` must
durably write both complete unchanged Agency outcomes outside the repository
before returning them to the normal scorer. Capture both process streams before
parsing. Keep the audited snapshot, Windows/Codex context, full tool union,
provider, requested and actual model, 15000 ms gate, and one-call fast budget
unchanged.

The equivalent unchanged CLI selection is:

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --case application-observability --case broad-python-typescript-application --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Record the exact two-line projection, aggregate bindings, receipts, safety,
disabled disclosures, and fairness validity. Compare each preserved plan,
proposal score, confidence, margin, and rejection reason with prior accepted
observations. If both Agency arms pass, make no product or policy change and
retain a further complete corpus as the next matched gate. If either safely
fails, change only genuinely general semantics proven by the complete outcome
and repeatable evidence. One configured-model plan shape is not permission for
a product or policy change.

## Verification

~~~text
.\.venv\Scripts\python.exe scripts\docs_metadata.py --check
.\.venv\Scripts\python.exe scripts\update_policy_availability.py --check
.\.venv\Scripts\python.exe scripts\update_worklog.py --check
.\.venv\Scripts\python.exe scripts\verify_docs.py
git diff --check
.\.venv\Scripts\python.exe scripts\context_handoff_status.py --json --threshold 50 --admission-threshold 65
~~~

## Constraints

- Check telemetry immediately before every live evaluation, including a
  conditional second run; require at least 65 percent remaining to admit it.
- At or below 50 percent, create a clean durable checkpoint and continue in the
  same task; do not dispatch a task or wait for telemetry to reset.
- Preserve every accumulated AR-119 commit and the clean branch.
- Do not weaken typed coverage, add a scenario route, raise the 15000 ms gate,
  increase the one-call budget, or reinterpret malformed upstream output.
- Do not claim Agency is better.
- Do not push, open or update a PR, trigger hosted Actions, mutate or close
  issue #132, or mark AR-119 complete.
- Update the canonical issue and replace this capsule when the package changes;
  create the required substantive and ledger commits.
