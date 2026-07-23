---
title: "Worklog: Record complete matched selection rerun"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, variance, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: a27f34061077d49bd097feed78e510b64aa32955
short: a27f340
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record complete matched selection rerun

## Purpose

Continue the matched-selection stability package from the clean recovery
checkpoint, preserve another complete configured-provider corpus without
weakening any gate, and determine whether a remaining Agency failure represents
a governed product defect or variable provider output.

## Approach

One complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, codex-subscription provider, requested and actual
gpt-5.6-luna model, and low reasoning effort. Stdout and stderr were captured
separately outside the repository before parsing, and their byte counts and
SHA-256 hashes were verified again before the report was read.

The complete report's one Agency failure received an immediate matched
runtime-routing-only confirmation with the same budgets and provider bindings.
The AR-119 checkpoint records both stream receipts, aggregate metrics, parity
bindings, the exact 19-line complete projection, the exact bounded projection,
and the remaining blocker.

## Challenges encountered

The complete corpus placed 18 of 19 Agency cases in a passing state. The
runtime-routing case abstained on low confidence, while five upstream provider
arms returned unknown disabled shadows or an invalid assignment row. The
malformed arms were retained as benchmark-validity failures and were never
counted as upstream losses.

The first raw multi-line projection containment check reported false because
the temporary artifact and edited Markdown used different newline sequences.
An exact case-sensitive line-by-line comparison then proved that all 19
projection lines matched with no substantive difference.

## Decisions and alternatives

No product or policy code changed. The runtime-routing Agency abstention passed
immediately under the same contract with complete typed coverage and no safety
defect. Changing planner normalization, staffing thresholds, typed coverage,
response parsing, the 15000 ms gate, or the one-call budget would have tuned
the governed contract to transient model output.

The next package remains in matched selection and starts with another unchanged
complete corpus. Contractor lifecycle, superiority claims, exact activation
proof, untouched-corpus statistics, and blinded completed-outcome trials stay
open.

## Verification

- The complete process finished in 444.622 seconds, emitted 1,187,735 bytes of
  valid JSON with no stderr, and preserved its verified stream hashes.
- Agency passed 18/19 with F1 0.905983, 18/19 complete typed coverage, p95/max
  latency 12484.032 ms, and zero forbidden, ineligible, or conflict
  selections.
- The immediate runtime-routing confirmation finished in 25.214 seconds,
  returned status 0, and passed with complete typed coverage, F1 0.857143,
  12799.429 ms latency, and every safety count at zero.
- Metadata passed for 289 Markdown files; policy availability, worklog-current
  for 115 commits, documentation validation for 289 Markdown files, exact
  19-line and bounded projection comparisons, and git diff --check passed
  before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as
validity failures, and do not advance to contractor lifecycle until one
complete Agency corpus passes safely.
