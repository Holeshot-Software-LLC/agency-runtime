---
title: "AR-206: Accept bounded ready routing receipts"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [product, evidence, hooks, routing, sqlite]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-206
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/194
depends_on: []
blocks: [AR-204]
---

# AR-206: Accept bounded ready routing receipts

## Problem

The durable preflight recipe admits structurally bounded routing decisions with
up to 2,048 JSON nodes, but the ready-receipt correlation verifier applies a
stale 256-node limit when it rereads the same authoritative decision. A valid
wide decision can therefore be stored and projected into a ready recipe, then
be rejected during Stop as `routing receipt evidence could not be verified`.
The resulting instruction to restore the evidence Store is misleading because
the Store and its receipt remain intact.

## Current state

The current Codex task reproduced the defect against its exact Store record.
SQLite integrity passes; the stored decision is 8,611 characters and 558 JSON
nodes; ordinary JSON decoding followed by the existing bounded projection
exactly matches the ready receipt. Only the verifier's smaller structural limit
causes the correlation failure. This task is already bound to an immutable old
hook launcher, so a source repair cannot retroactively make its Stop hook read
the new verifier.

## Approach

1. Make ready-receipt correlation use the same 2,048-node structural bound as
   the durable preflight recipe while retaining its 64,000-byte and depth-eight
   limits.
2. Add a focused regression whose valid routing decision exceeds 256 nodes and
   must round-trip through authoritative ready-receipt correlation.
3. Add a curated decision mutation that restores the legacy cap and must be
   killed by that regression.
4. Merge and exact-install the repair with the next authorized product build;
   prove the corrected Stop boundary in a fresh Codex task because existing
   tasks cannot replace their immutable hook launcher.

## Dependencies

AR-204 owns the integrated README-story proof. AR-205 owns inference-first
specialist staffing. This issue repairs only the authoritative evidence-reader
boundary exposed while pursuing those outcomes.

## Acceptance

- [x] The current Store is proven healthy and its wide routing decision exactly
  projects to the stored ready receipt under the durable recipe bound.
- [x] Ready-receipt correlation uses the durable 2,048-node recipe limit.
- [x] A focused warning-strict regression covers a valid decision above the
  former 256-node limit.
- [x] A curated decision mutation restores the defect and is assigned to the
  focused regression.
- [ ] The repair is committed, merged, and exact-installed.
- [ ] A fresh Codex task proves the installed Stop hook can read a valid wide
  ready receipt without a correction or evidence-unavailable response.
