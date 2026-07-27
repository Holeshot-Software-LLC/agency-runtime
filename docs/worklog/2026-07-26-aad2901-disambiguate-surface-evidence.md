---
title: "Worklog detail: Disambiguate surface evidence"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [testing, observability, reliability, windows]
related:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
supersedes: []
superseded_by: null
type: worklog
commit: aad2901879991862e199aacedf81a186700bd0d1
short: aad2901
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-158-disambiguate-multi-surface-observation-tests.md
---

# Worklog detail: Disambiguate surface evidence

## Purpose

Stop load-dependent observation ordering from rejecting correct MCP, HTTP, and
hook behavior during the measured Windows change loop.

## Approach

Affected tests now parse all bounded Agency observation records and select the
event owned by the assertion using surface, operation, and request ID where the
surface returns one. They continue checking every captured record for forbidden
request content. Each primary regression emits a valid unrelated Store event
first, proving it no longer relies on ambient ordering.

Store and runtime-boundary unit tests were hardened at the same seam. They
filter the Agency logger prefix and exact correlation fields while preserving
the intentional ordering in which nested Store evidence appears before the
enclosing boundary emits on exit.

## Challenges encountered

Two clean v2 source-byte controls passed, but the third run rejected one shard
after a 172.487 ms Store commit crossed the slow-query threshold. The Store and
MCP records each carried the correct distinct request ID; the test selected the
first record before checking its surface. The controller correctly withheld the
complete timing artifact. Because this test-only repair changes the exact
corpus digest, the two earlier controls cannot be mixed with replacement runs.

## Decisions and alternatives

Suppressing Store telemetry under load was rejected because the observation is
valid and useful. Raising the slow-query threshold or retrying until the test
passed was also rejected. Exact semantic selection makes the test reflect the
multi-surface production contract without changing product instrumentation.

## Verification

- Exact MCP, HTTP, and hook regressions: 3 passed, then 10 repeated invocations
  passed consecutively.
- Expanded runtime/store observation package: 11 passed warning-strict.
- Independent audit found no production correlation defect and approved the
  three primary fixes; lower-risk selectors were hardened in the same slice.
- Documentation and repository style checks passed.

## Follow-ups

Restart AR-156's three clean source-byte controls from the new ledger checkpoint;
do not reuse the earlier artifacts to generate weights. Full warning-strict
evidence and tracker creation remain outstanding.
