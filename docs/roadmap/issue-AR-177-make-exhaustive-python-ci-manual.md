---
title: "AR-177: Make exhaustive Python CI manual"
status: wont_do
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [ci, github-actions, cost, testing, coverage, performance]
related:
  - docs/decisions/0234-retire-superseded-manual-ci-checklist.md
  - docs/roadmap/acceptance/evidence/AR-177-manual-ci-reconciliation-20260907.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/decisions/0100-short-circuit-trusted-docs-only-pull-requests.md
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - .github/workflows/ci.yml
  - tests/test_ci_session_pair.py
  - tests/test_release_packaging.py
supersedes: []
superseded_by: docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
type: issue
epic: testing
issue_id: AR-177
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-177: Make exhaustive Python CI manual

> Retired September 7 under ADR-0234, not accepted against the old checklist.
> The manual-only implementation exists at 60543e1 and 222 current focused
> contracts pass. AR-186/ADR-0105 supersede its mandatory manual-run/release
> completion requirements. One retained manual hosted run failed at whitespace
> validation; no full topology pass or billing repair is claimed. The four
> shards, 97-percent floor, six compatibility sessions and original criteria
> below remain unchanged. No new exhaustive or Windows-native run was launched.

## Problem

The complete warning-strict Python corpus takes about 32 minutes locally and
its branch-instrumented form has historically taken about 69 minutes. Running
four coverage shards for every code pull request still consumes material raw
GitHub Actions minutes even when pairing limits wall time. Replacing coverage
with non-instrumented shards would not remove those runner envelopes.

## Current state

The coverage shard jobs, combined 97-percent report, and six-version
compatibility matrix run only on `workflow_dispatch`. Pull requests and pushes
skip them. The aggregate encodes the event-specific result: automatic events
require `skipped`; a manual event requires `success`.

Fast quality, a bounded Python production/security spine, dashboard UI coverage,
uninstrumented performance, Windows portability, cross-OS artifacts/parity, and
security gates retain their automatic behavior. Documentation-only pull
requests retain their separately governed five-runner lane.

## Approach

Gate the expensive job roots at the workflow level so no runner is allocated.
Keep job IDs stable for branch-policy compatibility and change visible names to
`integration`. Make the aggregate distinguish a deliberate automatic skip from
a required manual success. Preserve all underlying commands and thresholds for
on-demand production/release verification.

## Dependencies

ADR-0097 owns fail-closed fanout and the stable aggregate. ADR-0100 owns the
documentation-only lane. ADR-0101 records the explicit spend-versus-automatic-
coverage decision.

This is an exempt pre-tracker legacy record; no duplicate tracker is created
for its retirement. Current local/tracker parity checks still apply.

## Acceptance

- [x] Pull requests and pushes allocate no exhaustive Python coverage runner.
- [x] Pull requests and pushes allocate no six-version compatibility runner.
- [x] Manual dispatch requires all four coverage shards, the combined unchanged
  97-percent floor, and all six compatibility sessions.
- [x] The aggregate rejects success where an automatic skip is required and
  rejects skip, failure, cancellation, or missing evidence on manual runs.
- [x] Fast automatic production contracts and the docs-only lane remain intact.
- [ ] One manual hosted run measures the exact topology after Actions billing is
  repaired.
- [ ] The final repository release gate passes at the implementation commit.

## Implementation evidence

Automatic code PR/push primary topology drops from thirteen to ten allocated
runners by removing two coverage-pair jobs and one combine job. Main pushes
also stop allocating the three paired compatibility jobs. This is structural
workflow evidence, not a hosted timing or billing claim.

The retained 18-file production/security spine passed 521 tests with 5
platform skips in 65.03 seconds. The focused workflow/controller contract
package passed 145 tests in 13.00 seconds; Ruff and formatting checks and
`git diff --check` were clean.
