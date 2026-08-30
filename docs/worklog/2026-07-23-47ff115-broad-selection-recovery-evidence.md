---
title: "Worklog: Record broad selection recovery evidence"
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
commit: 47ff115dc94c9bd0918ba66d92c0c83121d7b532
short: 47ff115
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record broad selection recovery evidence

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve every Agency and upstream arm exactly, distinguish a
repeatable governed defect from configured-provider variance, and leave one
bounded next package without advancing to contractor lifecycle work.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate byte streams outside the repository before parsing, then byte
counts and SHA-256 hashes were independently verified.

The canonical AR-119 record preserves aggregate metrics, fingerprints,
receipts, and the exact compact projection of all 19 matched cases. The sole
Agency failure then received two broad-application-only matched confirmations
with no intervening product or policy change.

## Challenges encountered

The complete broad-application Agency arm exhausted the one-call workforce
budget, selected no worker, and truthfully recorded that inference was not
applied. The first bounded rerun applied inference below budget but omitted
only `accessibility-auditor`. The second bounded confirmation selected the
exact nine-worker team and passed a valid matched benchmark.

Three complete-run upstream arms were invalid: TypeScript returned an unknown
disabled shadow, application integration returned an invalid assignment row,
and the broad application returned another unknown disabled shadow. Those
arms remained errors and were not scored as upstream losses.

## Decisions and alternatives

No product or policy code changed. The complete-run failure recovered under
the same governed controls after one repeated accessibility omission, so
changing staffing semantics, weakening typed coverage, adding a scenario
route, increasing the one-call budget, relaxing the parser, or raising the
15000 ms gate would have tuned policy to variable provider output.

The next package starts with another complete corpus. If every Agency arm is
safe and passing but malformed or timed-out upstream provider arms alone keep
the benchmark invalid, record that exact blocker without weakening fairness
or response-contract gates.

## Verification

- The complete 19-case command ran in 404.782 seconds, returned status 1,
  emitted 1,183,286 stdout bytes and zero stderr bytes, and its saved hashes
  were independently reproduced.
- Agency passed 18/19 with zero forbidden, ineligible, or conflict selections,
  F1 0.839286, 18/19 complete typed coverage, and p95/max latency of
  13915.323 ms under the unchanged gate.
- The first bounded broad rerun omitted only `accessibility-auditor`; the
  second selected the exact nine-worker team and passed at 11532.017 ms with
  complete typed coverage and zero safety defects.
- All 21 roadmap projection lines matched the three saved machine-readable
  reports exactly. Provider, requested/actual model, receipt, call-count,
  latency-budget, fingerprints, invalid-arm, and broad-recovery assertions
  passed.
- Metadata for 298 Markdown files, policy availability, worklog-current,
  documentation validation for 298 Markdown files, and `git diff --check`
  passed before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Run one complete 19-case corpus immediately with
unchanged budgets and preserve the same exact projection. Keep every
activation, untouched-corpus, outcome, contractor-lifecycle, and release gate
open.
