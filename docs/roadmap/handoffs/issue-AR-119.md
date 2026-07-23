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
  - docs/worklog/2026-07-23-8918040-matched-latency-recovery.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-115-live-routing-trust
evidence_commit: 89180406a56b575c969b0dccbe60ae85f4dcc10e
minimum_ledger_commit: bb876f8390ffabbb0f24db911e5f5719cf919980
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
  89180406a56b575c969b0dccbe60ae85f4dcc10e.
- Minimum ledger commit:
  bb876f8390ffabbb0f24db911e5f5719cf919980.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  which remains open.
- The current HEAD may be newer than the minimum ledger commit but must contain
  it.

## Completed evidence

- ADR-0086 removed the context admission threshold while retaining the
  50-percent clean checkpoint. The latest committed recovery is `8918040` /
  `bb876f8`; telemetry never admits or blocks live work.
- That committed package preserved a 17/19 complete corpus with two latency-
  only misses followed by a valid 2/2 instrumented recovery. No product or
  policy rule changed.
- From clean `bb876f8`, the next unchanged complete corpus returned status 1
  in 454.014647 seconds. Its 1,182,655-byte stdout had SHA-256
  `b7d2f45e06703901b92d7c63272c4f6852c864b800d09915c1bb26792429e35b`;
  stderr was empty. The 12,702-byte exact projection had SHA-256
  `c0ae85f40b8667e21479d97693fb52e3f3c2dad4020f45b35a1d635f4b73545c`.
- All 38 arms retained the exact provider/model/receipt, applied-inference,
  one-call, and 15000 ms bindings. Corpus, roster, and allowed-agent
  fingerprints remained unchanged.
- Agency scored 15/19 with precision 0.925926, recall 0.862069, F1 0.892857,
  17/19 typed coverage, p50 8939.435 ms, p95/max 16712.282 ms, and zero unsafe
  selections. Installed release and runtime routing abstained; disabled LSP
  omitted its required disclosure; broad application exceeded latency with the
  complete expected team.
- Descriptive upstream scored 4/19 with precision 0.794872, recall 0.534483,
  F1 0.639175, 5/19 typed coverage, p50 14325.921 ms, and p95/max
  26469.788 ms. Two unknown-shadow and two invalid-assignment arms made the
  benchmark invalid; none is an upstream loss.

## Exact blocker

- Complete Agency corpora have varied from 19/19 to 18/19 and multiple 17/19
  observations. The newest corpus scored 15/19 on four distinct non-safety
  gates. Exact bounded confirmation is required before any defect claim or
  governed semantic change.
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
zero-call-validated instrumented matched confirmation for exactly these cases:

~~~text
installed-cross-platform-release
runtime-routing-integration-failure
disabled-lsp-winner
broad-python-typescript-application
~~~

Write every complete Agency outcome before projection and capture both streams
outside the repository. Keep the roster, tools, provider, model, low effort,
one-call budget, and 15000 ms gate unchanged. If all four pass, make no product
change. If a failure repeats, compare complete plan shapes and change only a
genuinely general governed defect. Keep malformed upstream arms invalid, never
losses.

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
