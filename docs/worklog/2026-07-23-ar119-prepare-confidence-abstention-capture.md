---
title: "Worklog: Prepare confidence-abstention capture"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: null
type: worklog
commit: be1ec78c6ef7eff0feaf5ff859a489de5920091d
short: be1ec78
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Prepare confidence-abstention capture

## Purpose

Preserve the completed non-live preparation for the next instrumented matched
selection package at the 50-percent hard checkpoint, while retaining the
65-percent live-evaluation gate and continuing in the same task.

## Approach

A pass-through Agency router was staged outside the repository for exactly
`application-observability` and `broad-python-typescript-application`. It
writes each unchanged complete `WorkforceInferenceOutcome` durably before
returning it to the normal matched scorer. A separate wrapper captures stdout
and stderr as raw bytes and records process metadata and hashes. A parser
preloads one accepted complete-corpus baseline and the newest failed-corpus
baseline, then retains exact projections, receipts, bindings, plan units,
proposal rankings, confidence, margins, and rejection evidence.

## Challenges encountered

The first zero-call parser check exposed that typed coverage is derived from
the four missing-coverage collections rather than stored as a per-arm field.
The helper was corrected before any provider call and both historical
baselines were then verified by byte count and SHA-256.

Telemetry fell to 42.3 percent after the preparation, below both the hard
checkpoint and live-admission thresholds. The package therefore records a
clean durable checkpoint but does not start the provider-backed evaluation.

## Decisions and alternatives

No product, policy, parser-contract, worker-contract, coverage, latency, or
call-budget behavior changed. Preparing the capture and comparison tooling is
not evidence that either confidence abstention is a stable defect. The live
package remains bound to the unchanged 15000 ms cold gate, one-call budget,
provider, model, roster, tools, and scorer.

No new task was created or awaited. The same task continues through normal
compaction and may start the live package only after a fresh admissible
telemetry reading.

## Verification

- The runner, wrapper, and parser passed Ruff check and format validation.
- Both runner and parser validations recorded zero provider calls.
- Validation retained generation 561, 272 workers, 247 available tools,
  `codex-subscription`, `gpt-5.6-luna`, low effort, and one fast call.
- The runner, wrapper, and parser SHA-256 values are respectively
  `446baf301481de9ffc907e656b93af4dceea31c2d1fec625bfec2436974671c3`,
  `de08aef192d322e2ee0558adefb4b4095298349c32251afb5f98b143eb6dbefa`,
  and `3f8f6fea7d035dc0eac65fdaa9e2bb3bbdefd6c6967e06c10775ce444d1be0ee`.
- Focused matched-selection tests passed 7/7.
- Metadata, policy availability, worklog, documentation, and diff checks
  passed before the substantive commit.

## Follow-ups

Run the prepared instrumented two-case package after an immediately preceding
telemetry reading admits live work. If both Agency arms pass, make no product
or policy change and retain a further complete corpus as the next matched
gate. If either safely fails, interpret only the preserved complete outcome
and repeatable general evidence. Do not claim Agency is better.
