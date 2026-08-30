---
title: "Restore the product hook activation boundary"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [codex, activation, hooks, delegation, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/handoffs/issue-AR-203.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 4314b8f65a21e40f18a22ca61b0d92654f967404
short: 4314b8f
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
---

# Worklog detail: Restore the product hook activation boundary

## Purpose

The final AR-203 product trial completed without an Agency route, header,
workspace sentinel, or any runtime cardinality. The ordinary product path still
used the stale ephemeral Codex launch contract and lacked the native-agent
controls already proven by the installation activation path.

## Approach

The product backend now persists the parent turn, enables
`multi_agent_v2` and `agents.enabled=true`, and requires hook children to
open the exact existing Agency Store. A product-canary-only environment switch
emits content-free accepted, completed, and failed stage counts for canonical
Codex hook events; the canary result and proof projection sanitize those counts
again before retaining them.

Product trials deliberately remain outside the activation canary's exact
single-child rollout parser because the product contract permits multiple work
units. Each Codex specialist launch instead receives an explicit
`fork_turns=none` instruction and its exact persisted native task name.

## Challenges encountered

The Windows restricted-token wrapper could not execute the repository patch
tool with split writable roots, so the repository-scoped Codex patch entrypoint
was used. Documentation verification also exposed two merge commits missing
from the worklog index; the canonical generator restored those rows before this
checkpoint.

## Decisions and alternatives

The repair reuses the existing behavioral activation and product-proof
decisions rather than adding a second orchestration contract. Raw stderr,
prompt content, arbitrary event names, persistent trust mutation, an added
write root, and a general sandbox bypass were rejected. Exact single-child
rollout parsing was also rejected for ordinary product trials because it would
invalidate correct multi-unit delegation.

## Verification

- Red tests failed on all prior launch, Store, hook-stage, proof-projection, and
  fork-isolation gaps.
- The repaired focused slice passes 26 tests.
- Ruff check and format checks pass for all changed Python and test files.
- Documentation metadata and validation pass for 549 Markdown files.
- `git diff --check` passes.

## Follow-ups

Complete decision-conformance mutation evaluation, two bounded review passes,
the named fast production spine, PR merge, exact Codex/ZCode installation, and
the separately authorized replacement ordinary canary under
[AR-203](../roadmap/issue-AR-203-prove-product-canary-write-and-activation.md).
