---
title: "Worklog detail: Bind Codex product execution"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [product, codex, delegation, workspace, evidence, testing]
related:
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
supersedes: []
superseded_by: null
type: worklog
commit: adad73292ca2d741bf242f4da629bf9057352376
short: adad732
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
---

# Worklog detail: Bind Codex product execution

## Purpose

Repair the two exact product boundaries exposed by consumed build `ff39761`:
its seven native specialist children completed, but product evidence rejected a
host-valid wait and no child could see the `workspace_write` value that assigned
the prompt-bound sentinel mutation.

## Approach

The product rollout projector now accepts the current Codex `wait_agent`
ceiling of 3,600,000 milliseconds while retaining strict arguments, output,
cardinality, and final-completion checks. The activation canary's separate exact
60,000-millisecond contract is unchanged.

Current inference-authored workforce descriptors now retain the verified
mutation scope. Exact reconstructed goals carry that value in a reserved
terminal suffix, including at the 4,096-character bound. The product child
contract tells every `workspace_write` child to check the prompt-bound sentinel
before its first mutation, create it only when absent, and leave it unchanged
otherwise. Read-only children and the non-working parent remain prohibited.

## Challenges encountered

The consumed private Codex rollout was correctly deleted with its isolated
profile, so the exact numeric wait value and child response bodies were not
retained. The host accepted and completed the call, while the content-free
diagnostic preserved the first rejected invariant. Store evidence independently
retained the exact implementation goal hash and verified mutation scope, which
made the missing child-visible scope reproducible without recovering private
content.

A broad optional file exposed seven legacy work-unit integrity failures. The
source and test are unchanged from `origin/main`; AR-222 records them without
expanding this product repair.

## Decisions and alternatives

Deterministic specialist selection, parent-authored workspace proof, weakening
the sentinel verifier, accepting a repaired header, and rerunning consumed live
evidence were rejected. Legacy four-field descriptors remain replayable, while
all current inferred descriptors carry the fifth verified scope field.

## Verification

- Consolidated focused slice: 127 passed, one deselected.
- Three new decision mutations: 3 killed, zero survived or invalid, source
  unchanged.
- Two bounded review passes completed.
- Named Python production spine: 656 passed, 6 skipped.
- Dashboard UI: 110 passed.
- Documentation metadata and integrity: 623 maintained Markdown files passed.
- Repo-wide Ruff lint and format checks passed; `git diff --check` passed.
- Routing evaluation passed every quality, performance, and scale threshold.
- Decision conformance: 84 killed, zero survived, zero invalid, source
  unchanged.

## Follow-ups

Merge without relying on hosted Actions, install the exact merge, spend one
autonomous activation and at most one fresh product trial, then update the local
evidence page and OpenClaw handoff from accepted runtime evidence.
