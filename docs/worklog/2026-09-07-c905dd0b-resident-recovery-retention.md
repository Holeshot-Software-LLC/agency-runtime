---
title: "AR-371 retention-aware resident recovery wrap-up"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [resident-managers, lifecycle, retention, verification]
related:
  - docs/roadmap/issue-AR-371-stalled-binding-makes-the-header-claim-none.md
  - docs/roadmap/acceptance/evidence/AR-371-next-turn-binding-recovery-20260907.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0152-fail-open-with-honest-header-when-no-specialist.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c905dd0b8ddfbcfb33a45286aaa0039ca3055cba
short: c905dd0b
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-371-stalled-binding-makes-the-header-claim-none.md
---

# Worklog detail: fix(residents): preserve retired-turn ordering during claim recovery (AR-371)

## Purpose

Finish the bounded next-turn recovery candidate and preserve the owner's clean
stopping point. Initial source checkpoint `c3b217f1` remains faithful history;
this correction ensures retention cannot make an older turn current again.

## Approach

Reuse the existing verified HMAC session digest and tombstone maximum sequence
barrier already used for authoritative finalization lookup. Reject retirement
at or beyond the incoming sequence before the unchanged full binding CAS. No
schema, identity storage, acknowledgment or native authority expansion.

## Challenges encountered

Live-run ordering alone omitted retired newer turns. Tombstones deliberately
retain no host field, so newer retirement in the same session is conservatively
blocking even across hosts. Older tombstones and other sessions do not block.
The four regressions create real Store tombstones, retire run rows and enter the
real ready transaction; they do not exercise a complete trim command.

## Decisions and alternatives

No new ADR: existing resident/fail-open and retired-identity contracts apply.
Do not infer a host from unavailable retired evidence, add retained correlation
data, weaken exact-trace Stop acknowledgment or reclaim on a plan/read call.

## Verification

The owner reopened focused execution for the stopping-point wrap-up. Exact
command and raw result are in the evidence receipt: 46 tests passed in 11.90s,
with no failed attempt. Scoped Ruff lint/format and diff checks passed;
metadata and strict local documentation checks passed for 1296 Markdown files.
Independent bounded source review reported no remaining scoped finding and
did not execute tests. Final telemetry showed 71.6% remaining.

## Follow-ups

Hand the clean candidate to the parent for normal in-progress publication,
combined installation and live evaluation. Tracker #521 stays open; broad-suite,
isolated acceptance and installed-native evidence are not supplied by this
package. No CI dispatch, provider/model call, native operation or owner Store
read/write was performed by this task.

Integration `bc778daf` includes published fallback receipt and static timeout repairs with exact merge ledgers. Frozen resident recovery and retirement-guard source remains unchanged; independent rows were preserved in the worklog.
