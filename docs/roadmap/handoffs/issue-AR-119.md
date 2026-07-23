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
  - docs/worklog/2026-07-23-0dfe777-second-19-case-agency-pass.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-115-live-routing-trust
evidence_commit: 0dfe777e87e0137433b199c015fcd994740c6974
minimum_ledger_commit: 644aec1b2d078a1060a48630e1af722a38181f93
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
  0dfe777e87e0137433b199c015fcd994740c6974.
- Minimum ledger commit:
  644aec1b2d078a1060a48630e1af722a38181f93.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  which remains open.
- The current HEAD may be newer than the minimum ledger commit but must contain
  it.

## Completed evidence

- ADR-0086 removed the context admission threshold while retaining the
  50-percent clean checkpoint. The latest committed recovery is `0dfe777` /
  `644aec1`; telemetry never admits or blocks live work.
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
- The zero-call-validated four-case instrumented confirmation returned status
  1 in 109.988309 seconds only because two upstream arms were malformed. Its
  768,427-byte stdout/report had SHA-256
  `2bc25b57ea7b5d86b36d8ef38bba1c2d6d510a88358b62a28814ed892181ac93`;
  the 3,350-byte projection had SHA-256
  `fb72cf528a86e079cee3b46e8cb60debaf803fa740826b845f006d6b2e239a50`.
- Agency passed 4/4 with complete typed coverage and disabled disclosure,
  p95/max 14074.396 ms, and zero unsafe selections. Every complete outcome was
  preserved before scoring. No product or policy rule changed.
- From clean `3e34c6f`, the next complete corpus returned status 1 in
  406.071759 seconds. Its 1,195,829-byte stdout had SHA-256
  `2e051f5aa2aa7b158a2ba799fde3ca9ff0e413a89fd587d0be740d090063b530`;
  the 13,313-byte projection had SHA-256
  `bab3fbf0c735603439914d284afc5a044d154b6e56f27715ef8dbdefbc6400c6`.
- Agency passed 19/19 with 19/19 typed coverage, complete disabled disclosure,
  p95/max 12942.243 ms, and zero unsafe selections. All 38 arms retained exact
  bindings. This is the second complete 19/19 Agency observation.
- Exactly one upstream arm, application observability, returned unknown
  disabled shadows. The benchmark remains invalid, and that arm is not a loss.
- From clean `644aec1`, the next corpus returned status 1 in 441.588810
  seconds. Its 1,189,496-byte stdout had SHA-256
  `c3d5276a257e3ec6fefd7a64ca1c24b1c852ae6ca12853a0c0d48864c7523707`;
  the 12,979-byte projection had SHA-256
  `72ff44fb13c003221bb623fbeb2d487ad1a170759eb8ff3f9c8fc9dff111524e`.
- Agency scored 17/19 with complete disabled disclosure and zero unsafe
  selections. Active incident abstained on margin; accounts payable omitted
  the required CFO review. Three upstream unknown-shadow arms kept the
  benchmark invalid.

## Exact blocker

- Two complete corpora have produced 19/19 Agency under unchanged controls,
  with intervening misses recovering in bounded confirmation.
- The newest corpus returned to 17/19; its two Agency failures require exact
  bounded confirmation. No complete corpus has produced 19 benchmark-valid
  upstream arms. Malformed, no-response, or timed-out arms remain validity
  failures, never comparative losses.

## Same-task continuity

- Context thresholds do not create, fork, dispatch, or wait for another task.
- Continue this package in the current task through normal Codex compaction.
- At or below 50 percent, ensure a clean durable checkpoint, then continue in
  the same task, including live evaluation.

## Next bounded work package

Stay in matched selection; do not advance to contractor lifecycle. Run one
zero-call-validated instrumented matched confirmation for exactly these cases:

~~~text
active-incident-containment
accounts-payable-cfo-separated
~~~

Preserve complete outcomes before projection and keep every control unchanged.
If both pass, make no product change. If either repeats, compare complete plans
with prior accepted outcomes and change only a genuinely general defect. Keep
malformed upstream arms invalid, never losses.

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
