---
title: "Repair actual packaged-dashboard accessibility and layout gaps"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, accessibility, browser, backlog]
related:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0032-adaptive-authenticated-dashboard-polling.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: d7231df3d7c01a8ea2518c7e3d8ee07a287dfabc
short: d7231df3
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
---

# Worklog detail: Repair accessible scroll and metric layout

## Purpose

Finish AR-138 from current evidence rather than repeat its already-implemented
coherence fixes. Browser QA of a fresh wheel reproduced real remaining defects:
navigation contrast around 3.2–3.5:1, empty-state contrast 4.19:1, unfocusable
scroll regions, generic groups with unsupported labels, and two metric cards
clipped beyond the desktop half-width panels. The old 375 px heading fix exists.

## Approach

Reuse the existing accessible muted color; give static scroll containers a
keyboard tab stop and meaningful region name; give named generic collections
group roles; use an auto-fitting metric grid. Add four unit regressions and an
optional reproducible real-browser checker. It serves an installed wheel with
a private Store, five audited fixture agents, stubbed host inspection and
denied outbound server connections. It never activates a native host or calls
a staffing provider. Playwright/axe live in a disposable development-tool prefix,
not the runtime dependency graph.

## Challenges encountered

The first diagnostic used historical coverage floors without the current source
include filter. It failed; the actual checked-in 95/86/93 command passed at
96.92/86.62/95.71. No CI threshold was changed.

Initial browser screenshots after a direct full refresh showed metric loading
states because that method cancels view-scoped reads. The checker now awaits
the same metric/evidence follow-ups as the UI, and requires a real control
request during its focus-preservation check. Initial structural receipts are
not substituted for final view-loaded evidence. Draft captures were moved
to the owned temporary QA directory, not deleted or published as final proof.

## Decisions and alternatives

ADR-0032 continues to govern source-owned, offline dashboard controls. No new
architectural decision or framework is needed. Do not weaken accessibility
checks, label mock DOM tests as browser proof, or conflate a private wheel
fixture with installed native-host support. AR-404's stale next-package wording
is aligned with the owner's current oldest-first order.

## Verification

- Four focused regression tests pass after red checks.
- Dashboard Python modules: 180 pass, 28.80s.
- Named fast Python spine: 1085 pass, three existing skips, 69.50s.
- Initial repaired-wheel structural browser check: 21 views at 1280/1024/375 px,
  zero axe violations or unexpected console/HTTP failures; dirty-field focus,
  selection and disclosures preserved; correlated failure and recovery observed.
- All ten packaged dashboard assets matched source. Final view-loaded evidence
  and independent acceptance remain pending at this source checkpoint.
- Ruff check/format (765 files), JavaScript syntax, docs and diff checks pass.

## Follow-ups

The final view-loaded browser receipt is committed at fa4d042b: 21 checks pass,
142 UI tests pass, and every focus-preservation check must issue a real control
poll. The acceptance schema required adding unchecked task markers to the
original six unchanged statements and classifying script citations as file
evidence rather than tests-directory evidence. No isolated verdict exists yet.
AR-138 still owns the six verdicts and PR/merge. Windows and native ZCode
activation remain separate operator holds; no backlog count changed here.
