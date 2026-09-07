---
title: "AR-154 current malformed-initial-page evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, pagination, evidence, acceptance]
related:
  - docs/roadmap/issue-AR-154-fail-malformed-initial-pages-closed.md
  - docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-154 current initial-page validation evidence

## Current implementation

Reviewed baseline: main 8b36ea28, PR #705; merge ledger c266715c.
The July 6a3bdaa repair is present. No runtime change is needed.

`validateCollectionPage` rejects non-record pages, non-array or oversized rows,
non-boolean truncation, absent/blank revisions and invalid cursor contracts.
Every truncated page requires a bounded canonical cursor; completed pages
require null. `completeCollection` validates the first page before copying rows
or fetching another page. Later pages are validated before append, and must
retain the initial collection and optional continuity revisions. Repeated
cursors and the 100-page boundary fail closed.

`fetchControlSnapshot` completes roster, snapshots and reviews before returning
a snapshot for commit. Full/manual and periodic control refreshes mark their
current failure stale without applying that failed snapshot. Workforce and
hiring have independently validated source commits, retaining last-good samples
or showing unavailable when there is no previous validated sample.

## Direct regression proof

The existing collection test directly rejects a missing initial cursor and
missing initial revision, asserting zero continuation requests. It also covers
positive two-page composition, changed revisions, malformed schemas and bounded
slug/encoded cursors.

Twelve new production-controller tests cover both `refreshAll` and
`refreshControlPlane`, each with roster, snapshots or reviews missing its first
cursor or revision. Each first loads valid nonempty data through that same
controller, then offers distinctly labeled uncommitted replacements. It asserts
no continuation request, unchanged configuration/hosts/roster/page metadata/
snapshots/reviews and live/control revisions, plus the visible stale notice.
These tests add direct state-preservation evidence; they do not replace a native
browser run or change production validation.

```bash
node --test --test-name-pattern='retains last-good state when initial' \
  tests/dashboard_ui.test.mjs
```

Twelve passed, zero failures/skips, 81.56ms.

## Fresh focused verification

```bash
PYTHONPATH=. python -m pytest tests/test_dashboard.py \
  tests/test_dashboard_server_coverage_complete.py \
  -k 'cursor or activity or observation' -q -W error
```

Thirteen passed, 190 deselected, zero failures/skips, 2.34s. This covers canonical
and hostile roster/collection cursors, activity page stripping and limits,
metadata-only activity/live projections, and content-free request observations.

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Complete UI: 188 passed, zero failures/skips, 256.64ms. Production coverage is
96.93% lines / 86.71% branches / 95.71% functions, passing the unchanged
ADR-0220 95/86/93 floors. This includes cursor validation, direct initial-page
state preservation and independent workforce/hiring stale/unavailable behavior.

## Exact-byte broader evidence

`git diff --exit-code 99e05d1f -- agency_runtime tests scripts
':(exclude)tests/dashboard_ui.test.mjs'` returns zero: the only test change is
the twelve-case JavaScript matrix. AR-151's
[final verification](AR-151-host-eligibility-20260907.md#final-current-verification)
therefore remains exact-byte Python/source evidence: 274 dashboard passes,
1085 named-spine passes with three existing skips, and all 39 routing gates.
These are reused receipts, not fresh executions in this package.

`git diff --exit-code 2ecde1a5 -- agency_runtime scripts` also returns zero.
AR-138's ten matching wheel assets and 21 loaded-view/viewport checks remain
same-byte evidence; its 184/184 decision-conformance result is scoped reuse for
unchanged Python implementation and selected tests, not a new install/evaluation.

## Acceptance boundary

All four original criteria are unchanged. No full corpus, aggregate Python
coverage, interpreter matrix, native Windows, provider staffing, hook activation
or hosted workflow is claimed. The builder supplies evidence only; all four
criteria require isolated verifier verdicts before completion.
