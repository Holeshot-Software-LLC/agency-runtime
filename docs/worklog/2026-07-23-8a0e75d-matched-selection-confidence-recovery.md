---
title: "Worklog: Record matched selection confidence recovery"
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
commit: 8a0e75d943e8ae79d872c9629be197a0354f6e21
short: 8a0e75d
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection confidence recovery

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
receipts, and the exact compact projection of all 19 matched cases. The two
fail-closed Agency cases then received one immediate two-case matched rerun
with no intervening product or policy change.

## Challenges encountered

Runtime-routing integration and the broad Python/TypeScript application both
failed closed on selection confidence in the complete corpus. Six upstream
arms returned unknown disabled shadows. Those malformed arms remained errors
and were not scored as upstream losses.

Both Agency failures recovered on the immediate bounded rerun. Runtime routing
selected its complete four-worker team, and the broad application selected its
exact nine-worker team. The bounded benchmark remained invalid because the
broad upstream arm returned another unknown disabled shadow.

## Decisions and alternatives

No product or policy code changed. Both complete-run confidence abstentions
recovered under the same governed controls on the first bounded rerun, so
changing staffing semantics, weakening typed coverage, adding a scenario
route, increasing the one-call budget, relaxing the parser, or raising the
15000 ms gate would have tuned policy to variable provider output.

The next package starts with another complete corpus. If every Agency arm is
safe and passing but malformed or timed-out upstream provider arms alone keep
the benchmark invalid, record that exact blocker without weakening fairness
or response-contract gates.

## Verification

- The complete 19-case command ran in 458.286 seconds, returned status 1,
  emitted 1,175,094 stdout bytes and zero stderr bytes, and its saved hashes
  were independently reproduced.
- Agency passed 17/19 with zero forbidden, ineligible, or conflict selections,
  F1 0.814815, 17/19 complete typed coverage, and p95/max latency of
  12421.974 ms under the unchanged gate.
- The bounded two-case rerun passed both Agency arms with 2/2 complete typed
  coverage, F1 0.960000, p95/max latency of 13077.683 ms, and zero safety
  defects.
- All 21 roadmap projection lines matched the two saved machine-readable
  reports exactly. Provider, requested/actual model, receipt, call-count,
  latency-budget, fingerprints, invalid-arm, and recovery assertions passed.
- Metadata for 299 Markdown files, policy availability, worklog-current,
  documentation validation for 299 Markdown files, and `git diff --check`
  passed before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Run one complete 19-case corpus immediately with
unchanged budgets and preserve the same exact projection. Keep every
activation, untouched-corpus, outcome, contractor-lifecycle, and release gate
open.
