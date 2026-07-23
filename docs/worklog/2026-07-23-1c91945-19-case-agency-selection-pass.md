---
title: "Worklog: Record 19-case Agency selection pass"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, stability, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 1c91945d120fcde20c98b79ea6ebc8a4525b73c8
short: 1c91945
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record 19-case Agency selection pass

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve every arm exactly, and determine whether the remaining
blocker was Agency selection stability or upstream benchmark validity without
advancing to contractor lifecycle work.

## Approach

The complete 19-case Windows corpus retained the predeclared 15000 ms cold
gate, one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate byte streams outside the repository before parsing. The complete
report, stream lengths, hashes, fingerprints, receipts, and exact 19-line
projection were then independently verified.

The canonical AR-119 record preserves every selection, safety count, disabled
disclosure, missing requirement, reason code, and fairness failure. Its current
requirements and next package now distinguish the achieved complete Agency
gate from the still-invalid comparative benchmark.

## Challenges encountered

Agency passed all 19 cases safely in one unchanged complete corpus for the
first time in the recovery sequence. The benchmark still failed closed because
five upstream provider arms were malformed: TypeScript, installed release,
application integration, and runtime routing returned unknown disabled
shadows, while the broad application returned an invalid assignment row.

Those arms cannot be scored as upstream losses. They invalidate the matched
comparison even though all Agency arms recorded complete parity bindings and
passed their own gates.

## Decisions and alternatives

No bounded rerun followed because no Agency arm failed. No product, policy,
parser, fairness, coverage, latency, or call-budget rule changed. Weakening any
of those gates would convert malformed upstream output into unsupported
comparative evidence.

The next package stays in matched selection and runs one further unchanged
complete corpus to seek valid upstream arms while testing whether the 19/19
Agency result repeats. Contractor lifecycle and every superiority, untouched-
corpus, activation, outcome, and release claim remain deferred.

## Verification

- The complete process finished in 413.433 seconds, returned status 1, emitted
  1,180,652 stdout bytes and zero stderr bytes, and its saved hashes were
  independently reproduced.
- Agency passed 19/19 with 19/19 complete typed coverage, precision 0.888889,
  recall 0.965517, F1 0.925620, p95/max latency 11665.961 ms, complete required
  disabled-winner disclosure, and zero forbidden, ineligible, or conflict
  selections.
- Five upstream arms remained errors, so benchmark validity and every
  superiority or release claim stayed false.
- All 19 documented projection lines matched the saved machine-readable report
  exactly. Provider, requested and actual model, receipt, call-count, inference,
  latency-budget, fingerprint, malformed-arm, and capture-hash assertions
  passed.
- Metadata for 300 Markdown files, policy availability, worklog currency for
  127 substantive commits, documentation validation for 300 Markdown files,
  and `git diff --check` passed before the roadmap recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Run one further complete 19-case corpus immediately
with unchanged budgets, capture both streams outside the repository, and retain
every invalid upstream arm as a benchmark-validity failure.
