---
title: "Worklog: Record matched selection reruns"
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
commit: 85afc03fccf789a6dca5cd68f294ff010dd92936
short: 85afc03
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection reruns

## Purpose

Continue the matched-selection stability package from the clean recovery
checkpoint, preserve complete configured-provider evidence without weakening
any gate, and determine whether the remaining Agency and upstream failures
represent governed product defects or variable provider output.

## Approach

Two complete 19-case Windows corpora kept the predeclared 15000 ms cold gate,
one-call fast budget, codex-subscription provider, requested and actual
gpt-5.6-luna model, and low reasoning effort. Every stdout and stderr stream
was captured outside the repository before parsing. The AR-119 checkpoint
records each aggregate, provider and parity binding, content hash, and exact
19-line compact projection.

The first complete run's three Agency failures received a three-case matched
rerun, four cold Agency-only instrumented calls, and a final matched
observability-only run. After observability recovered without a code change,
the second complete corpus ran unchanged. Its four Agency failures then
received one immediate matched four-case rerun.

## Challenges encountered

Neither complete corpus placed every Agency case in a passing state at the
same time. The first produced three fail-closed confidence or margin
abstentions. The second produced two fail-closed abstentions, one exact team
that exceeded the fixed latency gate by 216.664 ms, and one incomplete
clinical/legal team.

Every one of those second-run Agency failures passed immediately in the
bounded matched rerun, and the earlier observability failure passed four
instrumented calls plus a matched single-case run. Upstream provider responses
remained malformed in different case combinations, including unknown disabled
shadows and invalid assignment rows. Those arms were retained as benchmark
validity failures and were never counted as upstream losses.

## Decisions and alternatives

No product or policy code changed. The bounded evidence did not establish a
repeatable general semantic defect, and the broad application returned below
the unchanged latency gate. Changing planner normalization, staffing
thresholds, typed coverage, response parsing, the 15000 ms gate, or the
one-call budget would have tuned the governed contract to transient model
output.

The next package remains in matched selection and starts with another complete
corpus. Contractor lifecycle, superiority claims, exact activation proof,
untouched-corpus statistics, and blinded completed-outcome trials stay open.

## Verification

- Both complete reports parsed as valid JSON, emitted no stderr, retained all
  19 cases, and matched their roadmap projections exactly.
- The first complete run finished in 439.456 seconds; Agency passed 16/19 with
  F1 0.862069 and zero forbidden, ineligible, or conflict selections.
- The second complete run finished in 416.771 seconds; Agency passed 15/19
  with F1 0.898305 and zero forbidden, ineligible, or conflict selections.
- The final four-case rerun passed every Agency arm, complete typed coverage
  was 4/4, p95/max latency was 14055.499 ms, and every safety count was zero.
- Metadata, policy availability, worklog-current for 114 commits,
  documentation validation for 288 Markdown files, exact projection
  comparison, and git diff --check passed before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as
validity failures, and do not advance to contractor lifecycle until one
complete Agency corpus passes safely.
