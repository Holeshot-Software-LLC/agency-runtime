---
title: "Worklog: Record matched selection stability"
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
commit: e697f23105c67c06c6af3ce5c81aeb43e9ae2e35
short: e697f23
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection stability

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve every Agency and upstream arm exactly, distinguish
repeatable defects from configured-provider variance, and leave one bounded
next package without advancing to contractor lifecycle work.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. After the first process result
exceeded the calling tool's transient output envelope, the identical command
was rerun with stdout and stderr captured separately outside the repository.
Only that complete, parseable report was used as evidence.

The canonical AR-119 record now preserves aggregate metrics, fingerprints,
receipts, and the exact compact projection of all 19 matched cases. The three
Agency failures then received one bounded matched rerun with no intervening
product or policy change.

## Challenges encountered

The recoverable complete report contained three non-safety Agency failures:
one confidence-and-margin abstention, one omitted accessibility specialist,
and one independent-assurance abstention. It was also invalidated by an
invalid TypeScript upstream assignment and an unknown disabled shadow in the
broad-application upstream arm. All three Agency cases passed immediately on
the bounded rerun, while two upstream arms were malformed again but in a
different case combination.

Configured-provider output therefore remains variable. The first command's
unrecoverable output was excluded rather than reconstructed, malformed arms
were not scored as upstream losses, and bounded passes were not substituted
for the requirement that every Agency case pass together in one complete
corpus.

## Decisions and alternatives

No product or policy code changed. None of the Agency failures repeated, so
changing staffing semantics, weakening typed coverage, adding a scenario
route, increasing the one-call budget, relaxing the parser, or raising the
15000 ms gate would have tuned the product to transient evidence.

The next package starts with another complete corpus. If every Agency arm is
safe and passing but malformed or timed-out upstream provider arms alone keep
the benchmark invalid, record that exact blocker without weakening fairness
or response-contract gates.

## Verification

- The recoverable complete 19-case command ran in 426.748 seconds with no
  stderr and returned status 1 because Agency passed 16/19 and two upstream
  arms were malformed.
- Agency recorded zero forbidden, ineligible, or conflict selections. Its
  aggregate F1 was 0.879310, complete typed coverage was 17/19, and p95/max
  latency was 12490.811 ms under the unchanged gate.
- The bounded three-case rerun passed every Agency arm with exact helpful
  teams, F1 1.000000, complete typed coverage, zero safety defects, and
  p95/max latency of 14836.692 ms.
- The 19-line roadmap projection matched the saved machine-readable report
  exactly.
- Metadata, policy availability, worklog-current, documentation validation for
  287 Markdown files, and `git diff --check` passed before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Run one complete 19-case corpus immediately with
unchanged budgets and preserve the same exact projection. Keep every
activation, untouched-corpus, outcome, contractor-lifecycle, and release gate
open.
