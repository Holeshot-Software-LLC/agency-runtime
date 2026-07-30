---
title: "Worklog detail: Make recruiter repair partial and traceable"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [workforce, inference, recruiter, repair, evidence]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/handoffs/issue-AR-202.md
  - docs/roadmap/handoffs/issue-AR-203.md
  - docs/decisions/0115-aggregate-bounded-recruiter-repair-failures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: d470993845eff66b525f854ec10198973ab505c1
short: d470993
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
---

# Worklog detail: Make recruiter repair partial and traceable

## Purpose

Repair the first causal boundary from trial `ar203-830b878-ordinary-02` so the
inference-owned recruiter can correct rejected planned units and a repeated
failure remains attributable without storing provider content.

## Approach

The bounded retry now receives a distinct high-priority system contract that
requires exactly the failed planned-unit rows and explicitly omits rows already
retained by the same-provider accumulator. The ordinary recruiter continues to
produce the full plan. Durable route projection accepts only bounded,
allowlisted `unit_id` and `reason_code` pairs from the recruiter validation
contract and drops malformed, unknown, duplicate, or provider-authored detail.

Tests exercise the real initial and repair system prompts. Decision conformance
mutates both the repair-system binding and the durable failure projection so a
fake-provider shortcut or silently dropped diagnostic cannot pass the gate.

## Challenges encountered

The live trace showed only the generic contract rejection. Source inspection
found that the repair user prompt allowed partial output while the
higher-priority system prompt still prohibited omitting any planned unit. The
first test double did not inspect the system prompt and therefore missed that
contradiction. During mutation verification, one new mutation initially
survived because it targeted a direct parser test instead of the system-prompt
regression; correcting the test mapping killed the mutation without changing
production behavior. The dashboard runner's restricted attempt hit the known
Windows `spawn EPERM`; its authorized owner-context rerun passed.

## Decisions and alternatives

Online specialist ranking and selection remain inference-owned. The change
does not restore deterministic role anchors, increase the three-call fast
budget, weaken semantic validation, or force a hiring case when existing
specialists can form a safe team. ADR-0115 owns the partial-repair and durable
diagnostic boundaries.

## Verification

- The changed recruiter/routing boundary passes 107 tests with 1 skipped.
- Decision conformance passes its baseline and kills 21/21 mutations with zero
  survivors or invalid results; source inputs remain unchanged.
- The named fast Python spine passes 675 tests with 6 skipped.
- Dashboard UI passes 109 tests, and routing evaluation 1.3.0 passes every
  configured gate with routing p95 7.067 ms and cache-hit p95 1.430 ms.
- Documentation validation passes 551 files; Ruff checks and formats all 603
  Python inputs; `git diff --check` passes.

## Follow-ups

Open and merge the pull request, exact-install that merged revision for Codex
and ZCode only, and run one replacement README-story trial. If the same
recruiter boundary fails again, stop for owner direction. Otherwise require a
real accepted specialist team, or a defensible gap with an actual hiring
decision, under
[AR-203](../roadmap/issue-AR-203-prove-product-canary-write-and-activation.md).
