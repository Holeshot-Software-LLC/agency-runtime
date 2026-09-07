---
title: "Retire the duplicate mandatory coverage checklist without waiving diagnostic failures"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, testing, coverage, supersession]
related:
  - docs/roadmap/issue-AR-145-restore-python-release-coverage.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-145-instrumented-contracts-20260907.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0224
type: decision
deciders: [maintainers]
---

# ADR-0224: Retire the duplicate mandatory coverage checklist

## Context

AR-145 described July's failed branch-aware release run and repairs to
asynchronous observation, preflight ownership, synthetic benchmark isolation
and authority-boundary tests. The implementation at c3ffe6a7 remains, with later
contracts retained. Current source 7afa4b4d passes 41 focused cases under branch
instrumentation. No current whole-repository percentage is established.

ADR-0105 explicitly replaced the mandatory exhaustive completion/release gate.
The current workflow still offers the four-shard coverage diagnostic only on
manual dispatch and requires its combined 97-percent result when run. AR-176
already owns incomplete full-corpus/coverage evidence and specific stale
fixtures. Keeping AR-145 as a second mandatory release blocker misstates the
current delivery contract and duplicates that remaining work.

## Decision

Retire AR-145 as wont_do/superseded by AR-176, not as accepted against its
original checklist. Preserve every original criterion and historical failure,
including 96.66 percent and the incomplete final aggregate run. Keep its
working synchronization, authority and synthetic-benchmark tests.

AR-176 explicitly absorbs remaining fixture correctness and any aggregate
coverage gap reproduced when the owner requests that optional diagnostic.
Its known six stale fixtures remain open. Missing measurement is not a pass;
optional execution does not excuse a failed diagnostic or permit disabling tests.
Do not import the historical mandatory-release checkbox into ordinary delivery.

This decision applies ADR-0105; it does not supersede it or change any runtime,
test, coverage threshold, source/exclusion setting, workflow schedule or
release policy. No new permission to dispatch an exhaustive workflow is inferred.

## Consequences

One duplicate legacy checklist leaves the open queue without a false acceptance
verdict. Current scoped delivery is not forced into an unrequested exhaustive
run. The configured 97-percent diagnostic and remaining fixture/gap owner are
still explicit. AR-176 and the overall backlog remain unfinished.

## Alternatives

- Mark all five criteria satisfied: rejected because current aggregate and
  isolated full-suite evidence do not exist.
- Retain a second mandatory release blocker: rejected because ADR-0105 already
  replaced that operating rule and AR-176 owns the remaining diagnostic work.
- Delete the issue, disable its tests or relax 97 percent: rejected because
  historical failures and coverage controls remain valuable.
- Dispatch the exhaustive workflow now: rejected because oldest-first cleanup
  is not fresh authorization for that optional spend.

## Verification basis

At 7afa4b4d, focused branch instrumentation passes 41 tests in 12.08s.
The exact command and source boundaries are in the evidence record. Current
uninstrumented routing/performance results are preserved in AR-140's report,
not generated under coverage. No aggregate percentage, native Windows, hosted
workflow or cross-platform certification is claimed.
