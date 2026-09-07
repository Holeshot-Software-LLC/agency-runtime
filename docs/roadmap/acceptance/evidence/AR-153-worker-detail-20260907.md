---
title: "AR-153 current bounded worker-detail evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, workforce, evidence, acceptance]
related:
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md
  - docs/roadmap/acceptance/evidence/AR-138-repaired-dashboard-20260907.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-153 current worker-detail evidence

## Current implementation

Reviewed main baseline: 5a12f357, PR #704; initial merge ledger 26f3556b.
The earlier 6a3bdaa fix is present. No product or test edit is needed.

Store `get_workforce_worker_detail` validates an integer evidence limit within
1–1000, starts one read transaction, and obtains a worker and its current
recruitment contract. Hiring cases are filtered by target worker, proposed slug
or a lineage link before ordering and LIMIT. The same predicate determines the
total, so newer unrelated cases cannot displace matching evidence.

Lineage uses the same worker/version join for COUNT and limited row selection;
orphaned missing-version rows cannot create a count/record mismatch. Events,
outcomes and hiring cases also have exact total/truncation metadata. Exact
counts are SQL aggregates, not a claim of constant-time work at arbitrary scale;
record materialization remains limited. The snapshot test changes the worker
mid-read and requires a coherent pre-change projection.

HTTP bounds its page limit to 200, excludes retained history documents and
enforces a 2 MiB serialized response limit. A deliberately oversized detail
returns a generic 500 without exposing the private sentinel in body or logs.
The UI renders all delivered lineage/hiring rows and labels limited populations
as shown-of-total. It labels malformed totals unavailable, not as exact counts;
the separate 12-row history presentation cap has its own loaded-record notice.

## Fresh focused checks

```bash
PYTHONPATH=. python -m pytest tests/test_workforce_lifecycle.py \
  tests/test_dashboard.py -k 'worker_detail or workforce_worker_detail' -q -W error
```

Six passed, 193 deselected, zero failures/skips, 2.71s. Covers worker-filter-before-
limit, lineage totals/bounds, single snapshot, summary document omission,
HTTP readiness/count parity and generic response-budget failure.

```bash
PYTHONPATH=. python -m pytest tests/test_workforce_lifecycle.py -q -W error
```

Complete module: 25 passed, zero failures/skips, 8.08s.

```bash
node --test --experimental-test-coverage \
  '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
  --test-coverage-lines=95 --test-coverage-branches=86 \
  --test-coverage-functions=93 tests/dashboard_ui.test.mjs
```

Complete UI: 176 passed, zero failures/skips, 223.89ms; production coverage
96.93% lines / 86.70% branches / 95.71% functions. Unchanged 95/86/93 floors.
The worker UI case checks loaded records, total/truncation labels and malformed
metadata; not just counts or source-string matching.

## Exact-byte broader evidence

`git diff --exit-code 99e05d1f -- agency_runtime tests scripts` returns zero.
AR-151's [final verification](AR-151-host-eligibility-20260907.md#final-current-verification)
therefore applies to identical source and tests: six-module dashboard 274 pass
in 52.54s; named 29-module warning-strict spine 1085 pass/three existing skips in
68.98s; routing passes all 39 configured gates. These are reused receipts, not
fresh executions in this documentation-only package.

The repaired AR-138 wheel's ten dashboard assets/server source are unchanged;
its 21 loaded view/viewport checks remain same-byte evidence, not a fresh install.
Decision-conformance's 184/184 killed, zero survived/invalid result is scoped
reuse for unchanged implementation/selected tests, not a new mutation run.

## Requirement and acceptance boundary

ADR-0105 already supersedes a mandatory complete warning-strict corpus and
exhaustive coverage/interpreter matrix. AR-153 explicitly replaces only its old
fourth criterion with focused Store/dashboard suites plus the named production
spine. Original wording is retained; the first three criteria are unchanged.

No full corpus, hosted workflow, native Windows, native host or broad release
certification is claimed. All four current criteria require isolated verdicts;
the builder supplies evidence without judging them.
