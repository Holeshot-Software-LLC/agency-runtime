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
  - docs/worklog/2026-07-23-b8c1eca-bounded-selection-recovery.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-115-live-routing-trust
evidence_commit: b8c1eca4dfef5889ae50b99a01dda47a11b1f05a
minimum_ledger_commit: fe68e10cc6c2c3e82453ce4cc71c343342b11f08
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
  b8c1eca4dfef5889ae50b99a01dda47a11b1f05a.
- Minimum ledger commit:
  fe68e10cc6c2c3e82453ce4cc71c343342b11f08.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  which remains open.
- The current HEAD may be newer than the minimum ledger commit but must contain
  it.

## Completed evidence

- ADR-0086 removed the context admission threshold while retaining the
  50-percent clean checkpoint. The latest committed bounded recovery is
  `b8c1eca` / `fe68e10`; telemetry never admits or blocks live work.
- From clean `fe68e10`, the unchanged complete corpus returned status 1 in
  439.177328 seconds. Its 1,186,787-byte stdout had SHA-256
  `f5b8002c468e5bebef75db2f79aba3c7d3757bb61ed4fb26814b699a69f270bb`;
  stderr was empty. The 12,771-byte exact projection had SHA-256
  `d71a07c81d04dd48a23206e4fff5752a181bc4e2dab2df06dd3c6ddf6bd3bdfe`.
- All 38 arms retained the exact provider/model/receipt, applied-inference,
  one-call, and 15000 ms bindings. Corpus, roster, and allowed-agent
  fingerprints remained unchanged.
- Agency scored 17/19 with precision 0.888889, recall 0.965517, F1 0.925620,
  19/19 typed coverage, p50 8345.239 ms, p95/max 18099.353 ms, complete
  disabled disclosure, and zero unsafe selections. Brand/whimsy and PostgreSQL
  analysis selected the complete expected teams but exceeded the latency gate.
- Descriptive upstream scored 6/19 with precision 0.809524, recall 0.586207,
  F1 0.680000, 8/19 typed coverage, p50 12846.007 ms, and p95/max
  27643.450 ms. Three unknown-disabled-shadow arms made the benchmark invalid;
  none is an upstream loss.
- The instrumented two-case confirmation returned status 0 in 46.569601
  seconds. Its 711,421-byte stdout/report had SHA-256
  `f1326cd8de2848f4ee9d954e8e22d944a84875f82f1ae28789dfde48e9ea1608`;
  the 1,025-byte projection had SHA-256
  `64f23ffc44c96ecf931eb9eb2bbd24b31581d6a4ec3028680a544472cb6a98be`.
  Agency passed 2/2 within the latency gate. All four captured units had
  confidence and margin 1.0; no fairness or safety violation occurred.
- No product, selection-policy, parser, coverage, latency, or call-budget rule
  changed. The evidence establishes variance, not superiority.

## Exact blocker

- Complete Agency corpora have varied from 19/19 to 18/19 and multiple 17/19
  observations. The newest corpus produced all 19 correct, fully typed, safe
  selections but two exceeded the fixed latency gate; both immediately passed
  the identical bounded confirmation. This is latency variance, not a proven
  deterministic or semantic defect.
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
checkpoint. Capture both streams durably outside the repository before parsing.
Keep the audited snapshot, Windows/Codex context, full tool union, provider,
requested and actual model, 15000 ms gate, and one-call fast budget unchanged.

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --all --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Record the exact 19-line projection, aggregate bindings, receipts, safety,
disabled disclosures, and benchmark-validity failures. If Agency is not 19/19,
use bounded unchanged confirmation before considering any general semantic
change. Keep every malformed upstream arm as a validity failure, never a loss.

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
