---
title: "Worklog detail: Preserve turn-scoped specialist execution"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [product, codex, specialists, delegation, evidence, workspace]
related:
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0133-treat-product-specialist-loads-as-turn-scoped.md
supersedes: []
superseded_by: null
type: worklog
commit: e04397b76e38fc0997fb92b2160ffeef434a7bfb
short: e04397b
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
---

# Worklog detail: Preserve turn-scoped specialist execution

## Purpose

Repair the exact boundary exposed by the consumed `f8e607d` product trial. Its
eight inferred units completed through eight native Codex children, but one
`code-reviewer` served two units and therefore produced seven truthful
turn-scoped load rows. The former grader required eight loads, discarded the
first exact topology rejection, and could not prove a delegated workspace
write.

## Approach

Product proof now requires one load per selected specialist slug while keeping
one grant, consumption, delegation, worker lifecycle, native child, and prompt
delivery per unit. Reuse is accepted only when every correlated grant has the
same immutable specialist version and prompt hash. Product topology exceptions
map to bounded content-free codes only after baseline spawn/wait evidence is
present. Plan rendering carries verified mutation scope, opaque child delivery
names the decrypted native message as the exact goal, and the first delegated
write-capable unit owns the prompt-bound sentinel.

## Challenges encountered

The live topology used the second of two `code-reviewer` grants as the single
load anchor, so exact proof could not assume that a reused load points to the
first unit. The full 73-mutation evaluator also outlived two outer shell
ceilings and completed detached; its final JSON was not retained and is not
claimed. A captured changed-source slice provided an attributable exact-head
result instead.

## Decisions and alternatives

ADR-0133 supersedes ADR-0124's per-unit load cardinality. Duplicate fictional
load events, unanchored reuse, conflicting prompt identities under one slug,
parent-authored sentinel writes, and persisted raw exception text remain
rejected.

## Verification

- Exact product topology, host, delivery, and unit-plan suite: 102 passed.
- Named Python production spine: 643 passed, 6 skipped.
- Dashboard UI: 110 passed.
- Documentation: 615 Markdown files validated.
- Routing evaluation: all 39 correctness, performance, scale, and startup gates
  passed.
- Changed-source decision conformance: baseline passed; 22/22 mutations killed,
  zero survived or invalid, and `source_unchanged=true`.
- Two bounded review passes repaired diagnostic precedence, legacy
  `mutation_scope` hydration, sentinel-to-unit projection coverage, and the
  conflicting-identity negative case.
- Repository-wide Ruff lint/format and `git diff --check` passed.

## Follow-ups

Push and review the exact branch, merge without relying on hosted Actions,
install only the immutable merge, run one autonomous activation, and run at
most one fresh README product trial. Update the local evidence page and
OpenClaw handoff from that exact result; do not infer live success from this
local checkpoint.
