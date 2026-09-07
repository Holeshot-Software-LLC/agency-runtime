---
title: "AR-155 current bounded hiring-evidence delivery"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, hiring, evidence, acceptance]
related:
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md
  - docs/roadmap/acceptance/evidence/AR-154-initial-page-validation-20260907.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0220-measure-dashboard-coverage-over-production-modules.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-155 current hiring-evidence delivery

## Current implementation

Reviewed baseline: main 434175f0, PR #706; merge ledger f9efd6c9.
The July 6a3bdaa repair is present. No product or test change is needed.

Store collection SQL selects fixed lifecycle metadata, never the five evidence
columns. Summary rows set `evidence_included=false`. The page limit is 200,
with a 1 MiB byte budget and 16 KiB metadata reserve. HTTP enforces the same
1 MiB cap after response identity/pagination metadata are added. An oversized
Store summary or HTTP response fails generically with HTTP 500, without returning
the private sentinel.

Exact `case_id` lookup returns all five governed documents and marks
`evidence_included=true`, without the collection's 1 MiB cap. Tests require
exact document equality even when the complete exact response exceeds 1 MiB.

This is a serialized-response bound, not constant-memory whole-store work:
revision construction reads collection metadata, and the browser can follow
100 summary pages. The original 200-row document fanout is removed at SQL.

## UI evidence boundary

Summary rendering neither fetches nor renders embedded collection documents.
The explicit Load full evidence control requests one exact case. Validation
requires the case identity, full-evidence marker and all five documents.
A current request/commit generation and lifecycle guard precedes committing.
Deferred tests resolve the newer case first, then deliver the aborted older
response and require it to remain ignored. Failed loads retain the last-good
full case; lifecycle teardown cancels the request and prevents a late commit.

## Fresh focused checks

```bash
PYTHONPATH=. python -m pytest tests/test_workforce_lifecycle.py \
  tests/test_dashboard.py \
  -k 'hiring_collection or hiring_response_budget or worker_detail_hiring_summary' \
  -q -W error
```

Four passed, 195 deselected, zero failures/skips, 4.21s. Store and HTTP exercise
200-row pages containing a case with five large documents: every collection
row omits those fields, the response stays within budget, and exact lookup
preserves each document. Deliberate Store/HTTP oversize establishes fail-closed
budget enforcement.

```bash
PYTHONPATH=. python -m pytest tests/test_workforce_lifecycle.py -q -W error
```

Complete Store workforce module: 25 passed, zero failures/skips, 8.31s.

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Complete UI: 188 passed, zero failures/skips, 247.47ms. Production coverage
96.93/86.71/95.71 exceeds unchanged 95/86/93 floors. Includes explicit inspection,
full documents, malformed/wrong-case rejection, late old response rejection,
last-good retention and lifecycle-teardown cancellation.

## Exact-byte broader evidence

`git diff --exit-code e1c3069c -- agency_runtime tests scripts` returns zero.
All Python/source also equals 99e05d1f, excluding only the subsequently extended
`tests/dashboard_ui.test.mjs`. AR-151's
[final verification](AR-151-host-eligibility-20260907.md#final-current-verification)
is exact-byte reuse: 274 dashboard passes, 1085 named-spine passes with three
existing skips, and all 39 routing gates.

Product/scripts equal accepted AR-138 2ecde1a5; its ten matching wheel assets,
21 loaded-view checks and unchanged-Python 184/184 decision-conformance result
are reused receipts, not fresh installations or evaluations.

## Requirement reconciliation and limits

ADR-0105 makes exhaustive corpus, aggregate Python coverage and interpreter
matrix optional diagnostics. Only criterion 5 is explicitly reconciled to Store/
dashboard checks, UI production coverage and the named warning-strict spine,
with ADR-0220's unchanged UI floors. Original wording remains in the issue;
the first four criteria are unchanged.

No exhaustive corpus/coverage/matrix, hosted dispatch, native Windows, provider
staffing or installed-hook activation is claimed. The builder supplies evidence
only; five isolated verdicts are required before completion.
