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
  - docs/worklog/2026-07-23-3d0ee63-remove-live-context-admission-gate.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-115-live-routing-trust
evidence_commit: 3d0ee636f8f7451ca0e88d354ae9c8fd6b5a4691
minimum_ledger_commit: 27fcecc9bda22129949020bcbb69034620c3743c
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

This is the bounded bootstrap projection for the next AR-119 package. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) remains the
complete historical and acceptance contract.

## Checkpoint

- Branch: codex/ar-115-live-routing-trust.
- Substantive evidence commit:
  3d0ee636f8f7451ca0e88d354ae9c8fd6b5a4691.
- Minimum ledger commit:
  27fcecc9bda22129949020bcbb69034620c3743c.
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
- ADR-0086 removed the context admission threshold while retaining the
  50-percent clean checkpoint. Its substantive/ledger pair is `3d0ee63` /
  `27fcecc`; focused telemetry/schema tests passed 33/33 and docs validation
  passed for 318 Markdown files.
- From clean `27fcecc`, the instrumented two-case process returned status 0 in
  57.628651 seconds. Its 723,247-byte stdout/report had SHA-256
  `707f4a23fb46e3ea2d7ce85afb83dc0323e6cfcb9488e5aa32d6d3ad3ee5e320`;
  stderr was empty. The 2,119-byte exact projection had SHA-256
  `753f83abba79d4eb7e21babd956ff54e35d9fabe906aa62d4414d38ac15528f9`.
- The benchmark was valid. Agency passed 2/2 with precision 0.923077, recall
  1.0, F1 0.96, 2/2 typed coverage, p50 11767.710 ms, p95/max 13177.806
  ms, and zero safety selections. Descriptive upstream passed 1/2 with
  precision/recall/F1 0.75, 1/2 typed coverage, p50 16504.861 ms, p95/max
  19676.308 ms, and zero safety selections.
- Both complete Agency outcomes were captured before scoring. Application
  observability accepted four units; the broad application accepted seven.
  Every unit had confidence and margin 1.0, all bindings remained unchanged,
  and no fairness violation occurred.
- No product or selection-policy rule changed. This bounded recovery is not a
  complete-corpus result and is not a superiority claim.

## Exact blocker

- Complete Agency corpora have varied from 19/19 to 18/19 and multiple 17/19
  observations. The newest bounded confirmation recovered both prior
  confidence abstentions, but a further complete corpus is still required.
- No complete corpus has produced 19 benchmark-valid upstream arms. Malformed,
  no-response, or timed-out arms remain validity failures, never comparative
  losses.

## Same-task continuity

- Context thresholds do not create, fork, dispatch, or wait for another task.
- Continue this package in the current task through normal Codex compaction.
- At or below 50 percent, ensure a clean durable checkpoint, then continue in
  the same task, including live evaluation.

## Next bounded work package

Stay in matched selection; do not advance to contractor lifecycle. Run one
further unchanged complete 19-case Windows corpus from the new clean ledger
checkpoint. Capture stdout and stderr durably outside the repository before
parsing. Keep the audited snapshot, Windows/Codex context, full tool union,
provider, requested and actual model, 15000 ms gate, and one-call fast budget
unchanged.

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Record the exact 19-line projection, aggregate bindings, receipts, safety,
disabled disclosures, and fairness validity. If Agency is not 19/19, use
bounded unchanged confirmation before considering any general semantic change.
If upstream has malformed, no-response, or timed-out arms, keep the complete
comparison invalid and do not reinterpret them as losses.

## Verification

~~~text
.\.venv\Scripts\python.exe scripts\docs_metadata.py --check
.\.venv\Scripts\python.exe scripts\update_policy_availability.py --check
.\.venv\Scripts\python.exe scripts\update_worklog.py --check
.\.venv\Scripts\python.exe scripts\verify_docs.py
git diff --check
.\.venv\Scripts\python.exe scripts\context_handoff_status.py --json --threshold 50
~~~

## Constraints

- Check telemetry immediately before every live evaluation, including a
  conditional second run; the reading only determines whether a clean
  checkpoint must first be ensured.
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
