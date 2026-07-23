---
title: "Worklog: Record matched selection recovery evidence"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, latency, variance, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 2f2cfbb3139929a33a0c635b6d3e6f78eb31d9cb
short: 2f2cfbb
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection recovery evidence

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve its exact configured-provider evidence, and determine
whether its two Agency failures represented governed general semantic defects
before advancing AR-119.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate raw byte streams outside the repository before parsing, then
independently verified by byte count and SHA-256.

The two complete-run Agency failures received an immediate bounded matched
rerun under the same controls. The broad application recovered immediately.
Selection safety repeated a fail-closed confidence, margin, and latency
failure, then recovered with its exact specialist in a second bounded matched
confirmation. AR-119 records every stream receipt, aggregate, fingerprint,
provider/model binding, and the exact 19-line, two-line, and one-line compact
projections.

## Challenges encountered

The complete corpus produced a selection-safety confidence and margin
abstention plus a broad-application confidence abstention. Five upstream arms
returned malformed disabled-shadow contracts, so the complete benchmark
remained invalid and none was scored as an upstream loss.

The broad application recovered with its exact nine-worker team in the first
bounded rerun. Selection safety repeated once and exceeded the unchanged
latency gate, but its immediate single-case confirmation passed with the exact
specialist, complete typed coverage, and a valid matched benchmark. This
separated configured-provider plan-shape and latency variance from a
repeatable governed selection-semantic defect without weakening any fairness
or safety gate.

## Decisions and alternatives

No product or policy code changed. Both complete-run Agency failures passed
under the same governed controls in bounded confirmation, and each recovery
had complete typed coverage with zero forbidden, ineligible, or conflict
selections. Changing planner semantics, staffing thresholds, typed coverage,
response parsing, the latency gate, or the one-call budget would have tuned
policy to variable model output.

The next package remains in matched selection and starts with another unchanged
complete corpus. Malformed upstream arms remain benchmark-validity failures,
and no comparative superiority claim is allowed.

## Verification

- The complete process finished in 416.918 seconds, emitted 1,177,003 stdout
  bytes and zero stderr bytes, and preserved independently reverified stream
  hashes.
- Agency passed 17/19 with F1 0.828829, 17/19 complete typed coverage, and
  zero forbidden, ineligible, or conflict selections.
- The two-case rerun recovered the exact broad-application team; the
  selection-safety-only confirmation then passed with F1 1.000000, complete
  typed coverage, 7852.970 ms latency, and zero safety defects.
- All 44 captured arms preserved the expected provider, requested and actual
  model, receipt source, one-call count, applied-inference state, 15000 ms
  budget, roster fingerprint, and allowed-agent fingerprint.
- Metadata, policy availability, worklog-currentness, documentation validation,
  exact 19/2/1 projection comparisons against the raw captures, capture-hash
  verification, and `git diff --check` passed.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as validity
failures, and do not advance to contractor lifecycle until one complete Agency
corpus passes safely.
