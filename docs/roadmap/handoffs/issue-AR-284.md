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
evidence_commit: c514fb70b109adb2360758bafdb3bda2cd994e71
minimum_ledger_commit: 245a70c85d938027145443d2c91b371b79b0c746
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/754
---

# AR-284 provider fallback accounting recovery capsule

## Checkpoint

Implemented, verification deferred by owner direction. Metadata identifies
the inherited AR-411 clean source/ledger floor in base main e790c4d4; current
substantive/ledger checkpoint is indexed in the worklog. This capsule is not an
acceptance builder or completed-issue verdict. Tracker #754 is authorized.

## Completed evidence

Three real writers incorrectly used flattened stage/attempt order as fallback
count. Workforce/hiring loops now stamp exact provider-entry dispatch facts;
semantic repairs do not count as fallback. Optional metadata version 1 retains
stage, one-based ordinal, configured slot and actual prior-entry count.
Unknown/invalid counts become explicit wrapper SQL NULL. Legacy JSON and rows
remain unchanged; no schema migration. Focused regressions are written/unrun.

## Exact blocker

Source review and deferred focused tests/installed evidence remain. No runtime
success or all-provider telemetry claim. Uninstrumented producers and old
wrapper rows lack complete count provenance and remain explicitly unknown.

## Same-task continuity

Exclusive branch codex/ar284-receipt-fallback-semantics; parent coordinates
normal publication. Preserve other workers' source and records. Telemetry
crossed the 50-percent checkpoint threshold; finish this clean pair and
continue the same task without a new test/provider run.

## Next bounded work package

Give the parent the clean substantive/ledger head for bounded source review
and serial PR publication. When test execution is authorized, run the focused
attempt-accounting, Store, receipt-ingress and workforce/hiring regressions.
Do not generate a fresh inference failure solely for diagnostics.

## Verification

Targeted Ruff lint/format and diff checks only for source; tests, CI, native
calls, owner installation and isolated acceptance are deferred, not passed.
Static record checks may validate metadata/links without runtime execution.

## Constraints

No inference policy, model/profile, call budget, provider order, staffing,
owner Store or configuration change. No historical-row rewrite, schema bump,
implicit zero, coerced malformed count or inferred dispatch from status/name.
