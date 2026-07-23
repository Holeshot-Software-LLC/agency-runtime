---
title: "Worklog: Record matched corpus variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, latency, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 8af4cf09ba9a2408773ba2a361614ac3fd4d1284
short: 8af4cf0
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched corpus variance

## Purpose

Run the required complete matched-selection corpus from the clean recovery
checkpoint, retain the exact projection of every arm, distinguish Agency
failures from malformed upstream evidence, and leave one bounded next package
without advancing to contractor lifecycle work.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. The canonical roadmap record
now preserves aggregate metrics, fingerprints, receipts, and the exact compact
projection of all 19 Agency and upstream arms.

The two Agency failures received bounded reruns. Active incident containment
recovered with the audited incident responder. The LSP case first changed from
an exact but slow team to a fast fail-closed lifecycle-owner abstention, then a
direct diagnostic and a second matched rerun both produced the exact expected
four-worker team within the unchanged budget.

## Challenges encountered

The complete run produced two different non-safety Agency failures: an active
incident margin abstention and an 18068.738 ms LSP latency miss. Neither
repeated consistently under bounded reruns. The TypeScript upstream arm also
returned an unknown disabled worker, so the comparison remained invalid even
though its Agency arm passed.

Configured-provider output and latency therefore remain variable. A malformed
or timed-out arm cannot be reinterpreted as an upstream loss, while a later
bounded pass cannot be substituted for the requirement that every Agency case
pass together in one complete corpus.

## Decisions and alternatives

No product or policy code changed. The bounded evidence did not establish a
stable general semantic defect, so changing lifecycle ownership, weakening
typed coverage, adding a scenario route, increasing inference calls, or raising
the latency gate would have tuned policy to transient corpus output.

The next package starts with another complete corpus. Only a repeatable Agency
failure may justify a governed general semantic change followed by bounded and
complete reruns.

## Verification

- The complete 19-case command ran in 405.9 seconds and preserved all details;
  its command status was 1 because Agency passed 17/19 and one upstream arm was
  malformed.
- Agency recorded zero forbidden, ineligible, or conflict selections. Its
  aggregate F1 was 0.916667 and complete typed coverage was 18/19.
- The bounded active-incident rerun passed in 7348.709 ms with zero safety
  violations.
- The final matched LSP-only rerun passed with the exact expected team in
  8028.102 ms and returned a valid matched benchmark.
- Metadata, policy availability, worklog-current, documentation validation for
  286 Markdown files, and `git diff --check` passed before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Run one complete 19-case corpus immediately with
unchanged budgets and preserve the same exact projection. If every Agency case
passes but upstream provider arms alone invalidate the benchmark, record that
blocker without changing the parser or fairness gates. Keep every activation,
untouched-corpus, outcome, contractor-lifecycle, and release gate open.
