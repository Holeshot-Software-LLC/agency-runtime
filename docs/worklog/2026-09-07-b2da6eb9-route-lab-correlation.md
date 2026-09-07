---
title: "Bind diagnostic Route Lab receipts to request observations"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, diagnostics, correlation, backlog]
related:
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/acceptance/evidence/AR-173-route-lab-correlation-20260907.md
  - docs/decisions/0231-separate-route-lab-correlation-from-turn-persistence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: b2da6eb954ef0875745c2ddc17d6079567221de2
short: b2da6eb9
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
---

# Worklog detail: Route Lab correlation

## Approach and decisions

Trace attachment exists, but the exact HTTP regression claimed in AR-173 is
missing. Add two real social explanation requests with inference prohibited;
assert fresh UUIDs, current observation binding before explanation, exact
request/response/log correlation, bounded content-free fields and no durable
diagnostic turn/routing rows. Invalid and disabled calls cannot allocate a
routing trace. No production behavior changes.

ADR-0231 explicitly reconciles criteria 1/4/5 before review. Diagnostic-only
explanation code predates AR-173; the original persisted-routing narrative was
incorrect, not a missing feature to restore. The original wording remains.
Existing disabled bypass and ADR-0105 bounded verification continue to govern.

## Verification and checkpoint

The first regression alone passes; the expanded current focused pair passes
2 tests/173 deselections in 2.33s, with actual HTTP and SQLite assertions.
Ruff check/format and strict docs/diff pass. No failed production test or
inference call. At 40.9 percent telemetry, commit this safe tested slice and
its ledger; continue broader current verification and isolated acceptance.

## Follow-ups

Finish dashboard/explanation/observability suites, UI/current floors, named
spine and complete raw evidence before five isolated criteria. One normal
PR/merge before AR-174. Native Windows and owner activation/trust stay separate.

## Clean continuation

b2da6eb9 (b2da6eb954ef0875745c2ddc17d6079567221de2) records the focused test/requirement slice.
This immediate ledger is the clean checkpoint before broader verification.
