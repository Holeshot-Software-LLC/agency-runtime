---
title: "AR-284 provider fallback accounting recovery capsule"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, receipts, inference]
related:
  - docs/roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md
  - docs/roadmap/acceptance/evidence/AR-284-attempt-accounting-20260908.md
  - docs/decisions/0238-separate-provider-fallback-accounting-from-stage-order.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-284
branch: codex/ar284-receipt-fallback-semantics
evidence_commit: 3fb97e7dc1ebcbf91e87036b033a1b9274f5c6e7
minimum_ledger_commit: 607f9025e50f308f71ca60bbda3b082a2b2a4761
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/754
---

# AR-284 provider fallback accounting recovery capsule

## Checkpoint

Implemented, two bounded source passes clear, 161 focused cases passed in
2.58 seconds after the owner authorized wrap-up evaluation. Metadata identifies
the exact source/ledger floor; later integrations are indexed in the worklog.
This is not an acceptance verdict. Tracker #754 remains open.

## Completed evidence

Three real writers incorrectly used flattened stage/attempt order as fallback
count. Workforce/hiring loops now stamp exact provider-entry dispatch facts;
semantic repairs do not count as fallback. Optional metadata version 1 retains
stage, one-based ordinal, configured slot and actual prior-entry count.
Unknown/invalid counts become explicit wrapper SQL NULL. Legacy JSON and rows
remain unchanged; no schema migration. Three focused test files passed.

## Exact blocker

Exact-main installed evidence and isolated acceptance remain. No native
success or all-provider telemetry claim. Uninstrumented producers and old
wrapper rows lack complete count provenance and remain explicitly unknown.

## Same-task continuity

Exclusive branch codex/ar284-receipt-fallback-semantics; parent coordinates
normal publication. Preserve other workers' source and records. Telemetry
crossed the 50-percent checkpoint threshold; finish this clean pair and
continue the same task without a new test/provider run.

## Next bounded work package

Parent serially publishes the normal PR, then evaluates the combined exact-main
installation. Do not generate a fresh inference failure solely for diagnostics.

## Verification

Targeted Ruff lint/format/diff plus 161 focused deterministic tests passed.
No CI wait, native calls, owner installation or isolated acceptance in this
source package. Parent owns installed delivery as a separately recorded gate.

## Constraints

No inference policy, model/profile, call budget, provider order, staffing,
owner Store or configuration change. No historical-row rewrite, schema bump,
implicit zero, coerced malformed count or inferred dispatch from status/name.
