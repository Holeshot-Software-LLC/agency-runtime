---
title: "Restore owner provider selection"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, security, evidence, backlog]
related:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md
  - docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: a4be59b05d1918861f8d117e68c57331a681021b
short: a4be59b0
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
---

# Worklog detail: Owner provider selection

## Approach and decision

ADR-0117 restored owner controls, but AR-166's first criterion and one selector
still enforce the superseded read-only policy. Two tests fail against baseline
because valid options remain disabled. Change only the nonempty-list assignment.
The new interaction case checks second-provider selection, re-render stability,
exact staged secret target, redaction, four empty/invalid lists and recovery.
No backend/authentication/broker policy changes.

ADR-0229 explicitly reconciles only criterion 1 before review; original wording
and other five criteria remain. AR-298 already owns full bounded definitions;
do not restore the historical short preview or claim its broader issue complete.

## Verification

UI 189 passes, production coverage 96.93/86.71/95.71 against unchanged 95/86/93
floors, no skips/failures. Backend/owner five-module package 235 passes, 46.37s.
Fresh named spine 1085 passes/three existing skips, 67.88s. Ruff 766 files,
metadata/strict docs 1188 files, strict tracker 397 mapped/two historical PR
exceptions, policy/worklog/diff checks pass.

## Follow-ups

This is the clean repair checkpoint before a focused source-served browser
interaction. Then freeze all six rowsets, obtain isolated verdicts, publish one
PR and normal merge before AR-168. No installed-wheel, native Windows, attended
host activation, complete accessibility or real-provider staffing claim.

## Null HTTP error correction

f9c55ada repairs criterion 2 without changing any requirement: JSON null HTTP
errors threw TypeError and lost status/correlation. A red 401 case reproduces
it; the null-safe lookup passes 401/403/503. Full UI 190 passes, current coverage
floors pass; fresh named spine 1085/three existing skips, 66.99s; asset contracts
three pass/187 deselected. Backend/core source and its focused tests remain
identical to a4be59b0; strict docs/metadata pass 1190 files and tracker 397 mapped.

The source-served selector already passed 18 checks/zero POSTs at 1280/375.
The first zero-check timeout report is preserved: the browser fixture initially
injected the retired standalone config endpoint instead of combined control.
Final browser verification now adds null-401 terminal/correlation behavior;
all six builder rowsets remain pending, with no isolated review started.

## Final browser candidate

4a244776 retains the final source-served report and desktop/mobile screenshots.
All 20 checks pass, zero POSTs, including terminal null-401 notices with safe
request IDs. Served config/core hashes match f9c55ada exactly. The first fixture
timeout remains recorded; no production change was needed for its endpoint fix.
All six builder rowsets are present and pending. Strict docs pass 1190 files.
This is browser evidence for a private/offline source fixture, not an installed
wheel, native-host activation, whole-dashboard accessibility or staffing trial.

## Frozen review

f141583d freezes all six rowsets at 4a244776 and binds capsule/decision to the
same source and browser proof. All originals remain; only criterion 1 was
explicitly reconciled before review. Strict docs pass 1190 files. The first
isolated review follows this clean ledger, with no builder-assigned verdicts.

## First isolated review

bc28bf66 preserves all six first verdicts at 4a244776: 1 and 3–6 satisfy;
criterion 2 is absent because the supplied reconciliation test did not assert
IDs and the implementation was omitted from its bounded packet. Preserve these
results before inspecting that exact notice path and correcting the evidence.
No acceptance change or additional authority follows from this gap.

## Same-candidate citation correction

ad0a3b6e adds the existing dashboard-live.js:2451-2477 reconciliation forwarding
implementation to criterion 2's bounded packet at unchanged 4a244776. Both paths
forward the ID-bearing APIError message. Existing focused reconciliation test
passes (one test/four branches, 60.211025 ms); no product/test/candidate/criterion
change. First verdicts remain at bc28bf66. The other five accepted verdicts stay
unchanged; only criterion 2 receives the second and final ordinary review.

## Accepted completion

68936836 records all six criteria satisfied at 4a244776. The only recheck was
criterion 2's existing-implementation citation; the other five verdicts remain
unchanged, and every first result is preserved at bc28bf66. Two actual UI bugs
are fixed: disabled owner provider choices and null HTTP errors losing IDs.
ADR-0229 explicitly reconciles only the obsolete first criterion.

Final strict docs/metadata pass 1190 files, tracker parity 397 mapped/two
historical PR exceptions, policy/worklog/diff pass. Current queue: 40 mapped
plus 84 legacy, 124 unfinished. No native Windows, installed-wheel or host
activation claim. Publish one normal PR and merge before AR-168.
