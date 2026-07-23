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
  - docs/worklog/2026-07-23-ar126-persistent-goal-context-continuity.md
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

- A further one-case instrumented matched confirmation preserved the complete
  unchanged installed-release Agency outcome before projection. It returned
  status 0 in 23.807251 seconds; identical 690,970-byte report/stdout documents
  had SHA-256
  20d1e5791d25188f525920b009d07a8b759a088277a581c88739144b90417871,
  and stderr was empty.
- The benchmark was valid. Agency accepted at 6778.164 ms with
  cross-platform-installer-engineer, software-test-engineer, code-reviewer,
  test-results-analyzer, and cross-platform-release-verifier, complete typed
  coverage, one applied explicit-model call, and zero forbidden, ineligible,
  or conflict selections.
- The complete 56,678-byte Agency outcome had SHA-256
  de013181e16b869378d746b7a87b52f44c49cc79dd6f813e4260ccd04c48a704;
  the exact 767-byte projection had SHA-256
  c1ccfd1db84a7937de026edbdf43a5ae4ff114d57e85f1e7a87b029604de6bd1.
- The accepted plan hash was
  sha256:cf8a3f9b89d9c07525e361e68281fe008c83a4dc1e6afe1fafbdb6ffcbeba13b.
  Its first software unit required only implementation, selected the installer
  specialist at confidence/margin 1.0, and did not impose the prior
  generation-preparation requirement.
- The upstream arm returned complete typed coverage but exceeded the unchanged
  gate at 16711.509 ms. This remains descriptive evidence only. No product,
  policy, parser, worker-contract, coverage, latency, or call-budget rule
  changed.

## Exact blocker

- Installed release recovered under an unchanged bounded rerun. Its accepted
  alternative plan confirms the earlier generation-preparation occurrence was
  configured-model plan-shape variance, not a repeatable governed defect.
- The required complete 19-case confirmation has not yet run. The prior task
  stopped under the now-superseded cross-task handoff protocol after safely
  preserving the bounded result.
- Complete Agency corpora have varied from 19/19 to 18/19 and 17/19, and no
  complete corpus has produced 19 benchmark-valid upstream arms. Malformed,
  no-response, or timed-out upstream arms remain validity failures, never
  comparative losses.

## Same-task continuity

- Context thresholds do not create, fork, dispatch, or wait for another task.
- Continue this package in the current task through normal Codex compaction.
- Below 65 percent remaining, no new expensive live evaluation may start. At
  or below 50 percent, first preserve a clean durable checkpoint, then continue
  in the same task.

## Next bounded work package

Stay in matched selection; do not advance to contractor lifecycle. Run one
unchanged complete 19-case corpus. Capture both streams outside the repository
before parsing. Keep the audited snapshot, Windows/Codex context, full tool
union, provider, requested and actual model, 15000 ms gate, and one-call fast
budget unchanged.

The equivalent unchanged CLI selection is:

~~~text
.\.venv\Scripts\agency.exe eval upstream-selection --all --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
~~~

Record the exact 19-line projection, aggregate bindings, receipts, safety,
disabled disclosures, and fairness validity. If every Agency arm passes but an
upstream arm is malformed, absent, or timed out, preserve the exact invalidity
and do not score it as a loss. If an Agency arm safely fails, keep every control
unchanged and select the smallest next instrumented confirmation from exact
evidence. One configured-model plan shape is not permission for a product or
policy change.

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
