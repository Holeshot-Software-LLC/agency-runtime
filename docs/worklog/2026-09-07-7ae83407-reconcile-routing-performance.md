---
title: "Reconcile implemented routing performance with runner evidence"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, performance, evidence]
related:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/acceptance/evidence/AR-140-current-performance-20260907.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 7ae8340752c4223422fd943184b255ebb459ae52
short: 7ae83407
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/701
related_issues:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
---

# Worklog detail: Reconcile implemented routing performance

## Approach

Inspect current source and existing authority before treating the July issue as
new work. The bounded caches, exact fingerprint/generation binding, sparse
retrieval, batched reconciliation, lazy startup and explicit budgets already
exist. ADR-0121 replaces the old selection interpretation with candidate recall
and a labelled synthetic cache probe; it does not remove performance gates.

## Challenges and alternatives

The old Current state described resolved defects and machine-specific historic
times as if they were still current. Preserve them as historical observations,
add the exact current report, and keep the original five criteria unchanged.
Neither reimplementing the fixes nor calling local passing numbers supported-
runner certification would resolve the actual remaining evidence obligation.
Real 75-second staffing latency remains separate under AR-253.

## Verification

All 39 current versioned Linux gates pass. Narrowing/cache p95 are 1.081/0.201 ms;
version startup median is 16.989 ms. Every retrieval tier passes with unchanged
hashes, samples and budgets. Focused tests: 135 pass/two performance tests
deselected (20.04s), plus 67 pass (1.48s); standalone eval supplies the complete
performance result. Product/tests/scripts equal accepted AR-138 candidate
2ecde1a5, so its named spine/UI/conformance receipts are reused with that scope,
not presented as new runs. Metadata, policy, docs and strict tracker checks pass.

## Follow-ups

Retain AR-140 for pinned isolated supported-runner evidence, including the
owner's Windows arm, then isolated acceptance. No code, test, budget, acceptance
or count change. Publish one PR; AR-145 follows. AR-404 stays open.
