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

## Complete evidence candidate

f4f5124e (f4f5124ef6433db9cae18784c15cc76ba880b391) contains actual full-focused 195-pass/52.75s,
UI 204-pass/257.107362ms/96.93-86.78-95.73 coverage, and named-spine
1085-pass/three-existing-skips/69.18s receipts. All strict record gates pass
for 1206 Markdown files, 397 mapped/two historical PR exceptions, Ruff and diff.
Draft missing-heading and copied display-padding failures are retained in the
receipt; neither was ignored or claimed as passed. No code changes after
b2da6eb9; the complete packet is ready for five isolated checks.

## Acceptance freeze

017dea36 freezes f4f5124ef6433db9cae18784c15cc76ba880b391 for all five isolated checks.
No source/test changes follow the passing receipts. ADR-0231 reconciliation
precedes any verdict and retains original wording.

## First isolated review

941b9025 preserves all five first-pass verdicts at f4f5124e: 1/3/4/5 satisfy,
2 is contradicted because the observation carries the trace digest, not the
raw response trace. This is a remaining wording defect, not a production
failure. Preserve the original and explicitly supersede ADR-0231 for the
representation clarification; then use one second/final all-criteria review.

## Final candidate

594bc4d3 (594bc4d3939d144440ae52f5acdf5f840c79f25e) explicitly supersedes ADR-0231 with ADR-0232;
criterion 2 now requires the observation digest to equal the domain-separated
digest of the response trace. Original wording and first verdicts at 941b9025
remain. No product/test/script change versus f4f5124e (Git diff exits zero).
Fresh strict records pass for 1207 Markdown files and 397 mapped/two historical
PR exceptions. Staged whitespace checks caught an extra new-ADR EOF blank
before commit; it was removed. All five criteria need new final verdicts.

## Final review freeze

7650cdf0 freezes 594bc4d3939d144440ae52f5acdf5f840c79f25e for the second/final review.
The clean checkpoint precedes isolated evaluation; no third review by default.
