---
title: "Worklog: Record matched selection recovery"
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
commit: a7787486123c7378671fe65ab19897c1e3a7e7bd
short: a778748
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection recovery

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve its exact configured-provider evidence, and determine
whether its three Agency failures represented governed general semantic defects
before advancing AR-119.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate raw byte streams outside the repository before parsing, then
verified by byte count and SHA-256.

The three complete-run Agency failures received one immediate bounded matched
rerun under the same controls. Runtime routing and the broad application
recovered immediately. Application observability instead failed closed after
the one-call staffing budget was exhausted, so it received one final
observability-only matched confirmation. AR-119 records every stream receipt,
aggregate, fingerprint, provider/model binding, and the exact 19-line,
three-line, and one-line compact projections.

## Challenges encountered

The complete corpus produced an observability confidence abstention, a
204.514 ms runtime-routing latency miss after selecting the complete team, and
a broad-application selection that omitted only `accessibility-auditor`. Four
upstream arms were malformed, so the complete benchmark remained invalid and
none was scored as an upstream loss.

Runtime routing and the broad application passed in the immediate bounded
rerun. Observability failed closed with `workforce_call_budget_exhausted` and
truthfully recorded that staffing inference was not applied after the unchanged
one-call budget was consumed. It then passed in the immediate single-case
confirmation with complete typed coverage and a valid matched benchmark. This
separated configured-provider plan-shape and latency variance from a repeatable
selection-semantic defect without weakening any fairness or safety gate.

## Decisions and alternatives

No product or policy code changed. All three complete-run Agency failures
passed under the same governed controls in bounded confirmation, and each
recovery had complete typed coverage with zero safety defects. Changing planner
semantics, staffing thresholds, typed coverage, response parsing, the latency
gate, or the one-call budget would have tuned policy to variable model output.

The next package remains in matched selection and starts with another unchanged
complete corpus. Malformed upstream arms remain benchmark-validity failures,
and no comparative superiority claim is allowed.

## Verification

- The complete process finished in 457.161 seconds, emitted 1,185,651 stdout
  bytes and zero stderr bytes, and preserved verified stream hashes.
- Agency passed 16/19 with F1 0.888889, 18/19 complete typed coverage, and zero
  forbidden, ineligible, or conflict selections.
- The three-case rerun recovered runtime routing in 8344.524 ms and the exact
  broad team in 12212.504 ms, both with complete coverage and zero safety
  defects.
- The observability-only confirmation passed in 9885.533 ms with complete
  coverage, F1 0.857143, and zero safety defects; its benchmark was valid.
- All applicable captured arms preserved the expected provider, requested and
  actual model, receipt source, one-call count, 15000 ms budget, roster
  fingerprint, and allowed-agent fingerprint. The bounded observability
  budget-exhaustion arm truthfully retained `inference_applied=false`.
- Metadata passed for 293 Markdown files; policy availability, worklog-current
  for 119 substantive commits, documentation validation for 293 Markdown files,
  exact 19/3/1 projection comparisons with capture-hash verification, and
  `git diff --check` passed.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as
validity failures, and do not advance to contractor lifecycle until one
complete Agency corpus passes safely.
