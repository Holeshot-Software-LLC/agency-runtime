---
title: "Worklog detail: Authorize the exact Codex product delegation plan"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [codex, product, delegation, authority, mutation]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 420356a
short: 420356a
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
---

# Worklog detail: Authorize the exact Codex product delegation plan

## Purpose

Repair the first failed edge from the consumed `dd85e7d` product trial. That
trial proved inference selected eight fitting specialists, but the Codex parent
launched none of them because the product backend did not provide the explicit
high-priority delegation authority used by the passing activation canary.

## Approach

Supply a source-controlled Codex developer instruction only in Agency-mode
product trials. The instruction makes the parent a collaboration-only scheduler
for every exact accepted plan row, preserves dependency order and exact native
labels/goals, and limits ready waves to three children. Hook-injected specialist
children perform their exact assignments without recursively delegating.

Keep native-only product trials free of the Agency instruction. Add focused
tests for the encoded Codex configuration and both parent/child branches, then
add curated mutations for removing the authority and leaking it into
native-only mode.

## Challenges encountered

The first review pass found that placing the instruction in the shared product
option tuple would also expose it to native-only trials. The option builder was
split into Agency and native-only variants before checkpointing. The work-unit
projection was also confirmed to place the complete correlated request in each
child goal, so the first delegated workspace writer still receives the exact
harness proof instruction while the parent remains prohibited from product
tools.

## Decisions and alternatives

[ADR-0126](../decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md)
records the bounded authority boundary. The implementation does not hard-code a
team, permit parent fallback, or allow recursive children; inference and the
persisted plan remain authoritative.

## Verification

- Two bounded review passes completed; the native-only scope finding was fixed.
- All 21 warning-strict product-host tests passed.
- The curated manifest anchor test passed.
- Both new focused decision mutations were killed with zero survivors or
  invalid results, and the source tree was unchanged.
- Ruff check, Ruff format, metadata checks, policy availability, worklog
  generation, `git diff --check`, and documentation validation passed for 588
  Markdown files.
- The AR-207 recovery capsule remained within its 180-line and 12-KiB bounds.

## Follow-ups

Run the named fast verification spine, review and merge the exact revision,
exact-install Codex, ZCode, and dashboard, then spend the new build's single
activation and product trials. The local evidence page and OpenClaw handoff
remain gated on live proof.
