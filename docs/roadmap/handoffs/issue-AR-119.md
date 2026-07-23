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
  - docs/worklog/2026-07-23-fc9c453-confidence-abstention-recovery.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-115-live-routing-trust
evidence_commit: fc9c453b360f2274b4afd03ffa4df3ce61e97aa0
minimum_ledger_commit: 160c2dd0ef544ac920e9512cea3bd4f3d513b935
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
  fc9c453b360f2274b4afd03ffa4df3ce61e97aa0.
- Minimum ledger commit:
  160c2dd0ef544ac920e9512cea3bd4f3d513b935.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  which remains open.
- The current HEAD may be newer than the minimum ledger commit but must contain
  it.

## Completed evidence

- ADR-0086 removed the context admission threshold while retaining the
  50-percent clean checkpoint. The two-case recovery was committed as
  `fc9c453` / `160c2dd`.
- From clean `27fcecc`, the instrumented application-observability/broad-
  application process returned status 0 in
  57.628651 seconds. Its 723,247-byte stdout/report had SHA-256
  `707f4a23fb46e3ea2d7ce85afb83dc0323e6cfcb9488e5aa32d6d3ad3ee5e320`;
  the exact projection was 2,119 bytes with SHA-256
  `753f83abba79d4eb7e21babd956ff54e35d9fabe906aa62d4414d38ac15528f9`.
  Agency passed 2/2; every captured unit had confidence and margin 1.0.
- From clean `160c2dd`, the further unchanged complete corpus returned status
  1 in 414.999636 seconds. Its 1,183,103-byte stdout had SHA-256
  `01ada91b3c40baf34647b9230a23eedd61fbb667cbedb1647a27d3eb601ac831`;
  stderr was empty. The 12,946-byte exact projection had SHA-256
  `7f8c9634b74eccd44cfca76480246a6e9a87baa6231480ab0e14d0bc92430db8`.
- Agency passed 17/19 with precision/recall/F1 0.896552, 17/19 typed
  coverage, p50 7868.567 ms, p95/max 11363.777 ms, complete required disabled
  disclosure, and zero forbidden, ineligible, or conflict selections.
  Application observability abstained on confidence; selection-safety review
  abstained on margin. Broad application passed.
- All 38 arms retained the exact provider/model/receipt, applied-inference,
  one-call, and 15000 ms bindings. Corpus, roster, and allowed-agent
  fingerprints remained unchanged.
- Descriptive upstream passed 4/19 with precision 0.743590, recall 0.500000,
  F1 0.597938, 8/19 typed coverage, p50 13078.001 ms, and p95/max
  21629.692 ms. Five arms returned unknown disabled shadows, so the benchmark
  is invalid and none is an upstream loss.
- No product or selection-policy rule changed. Neither run establishes
  superiority.

## Exact blocker

- Complete Agency corpora have varied from 19/19 to 18/19 and multiple 17/19
  observations. The newest corpus failed application observability immediately
  after its bounded recovery and newly failed selection-safety review; this is
  variance, not a proven deterministic defect.
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
instrumented matched confirmation of `application-observability` and
`selection-safety-review`. A pass-through `agency_router` must durably write
both complete unchanged Agency outcomes outside the repository before returning
them to the normal scorer. Capture both process streams before parsing. Keep
the audited snapshot, Windows/Codex context, full tool union, provider,
requested and actual model, 15000 ms gate, and one-call fast budget unchanged.

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --case application-observability --case selection-safety-review --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Record the exact two-line projection, complete plan units, deterministic
proposal scores, confidence, margins, rejection reasons, aggregate bindings,
receipts, and validity failures. Treat recovery as variance unless a genuinely
general, repeatable defect is proven.

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
