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
commit: 71f77755191403e53418a6eb6afb6665dd68dfef
short: 71f7775
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
whether its latency and fail-closed Agency failures represented a governed
general semantic defect before advancing AR-119.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate raw byte streams outside the repository before parsing, then
independently verified by byte count and SHA-256.

The two complete-run Agency failures received two bounded matched runs under
the same controls. The first remained fail-closed, while the second restored
complete typed coverage and passed both cases. AR-119 records every stream
receipt, aggregate, fingerprint, provider/model binding, and the exact 19-line,
two-line, and two-line compact projections.

## Challenges encountered

Runtime routing selected its complete typed team in the full corpus but missed
the unchanged gate by 154.956 ms. Active incident containment abstained on
selection margin. Six upstream arms returned malformed assignment or disabled-
shadow contracts, so the complete benchmark remained invalid and none was
scored as an upstream loss.

Both Agency cases abstained safely in the first bounded rerun. Both then passed
with complete typed coverage in the second bounded confirmation, where the
runtime-routing upstream arm returned an unknown disabled shadow. This
separated configured-provider plan-shape and latency variance from a repeatable
governed selection-semantic defect without weakening a fairness or safety gate.

## Decisions and alternatives

No product or policy code changed. Both complete-run Agency failures passed
under the same governed controls in bounded confirmation with complete typed
coverage and zero forbidden, ineligible, or conflict selections. Changing
planner semantics, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would have tuned policy to variable model
output.

The next package remains in matched selection and starts with another unchanged
complete corpus. Malformed upstream arms remain benchmark-validity failures,
and no comparative superiority claim is allowed.

## Verification

- The complete process finished in 415.027 seconds, emitted 1,179,789 stdout
  bytes and zero stderr bytes, and preserved independently reverified stream
  hashes.
- Agency passed 17/19 with F1 0.916667, 18/19 complete typed coverage, and
  zero forbidden, ineligible, or conflict selections.
- The second two-case confirmation passed both Agency cases with F1 0.800000,
  complete typed coverage, p95/max 10140.279 ms, and zero safety defects.
- All 46 captured arms preserved the expected provider, requested and actual
  model, receipt source, one-call count, applied-inference state, 15000 ms
  budget, roster fingerprint, and allowed-agent fingerprint.
- Metadata, policy availability, worklog-currentness, documentation validation,
  exact 19/2/2 projection comparisons against the raw captures, capture-hash
  verification, and `git diff --check` passed.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as validity
failures, and do not advance to contractor lifecycle until one complete Agency
corpus passes safely.
