---
title: "AR-209: Bind opaque Codex child launches to exact plan rows"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [codex, delegation, activation, product, security, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-209
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/203
depends_on: []
blocks: [AR-203, AR-204, AR-207]
---

# AR-209: Bind opaque Codex child launches to exact plan rows

## Problem

Codex encrypts an arbitrary collaboration message before Agency's
`PreToolUse` hook sees the native spawn. Agency therefore cannot compare the
visible value with the persisted plaintext work-unit goal. The existing
recovery path admitted only the fixed package-owned activation canary. That
made exact activation pass while an ordinary product spawn was denied before
any child started.

Two retained real-host traces record the exact denial: the unencrypted native
task label matched the planned row, while the `message` was an opaque
`gAAAAA...` value and failed plaintext goal equality. The consumed
`584b949` product trial shows the corresponding graph: one parent spawn and
one output, but zero child starts, waits, grants, loads, or workspace writes.

## Current state

The source candidate introduces a Codex-only v2 child context. A strictly
shaped opaque message is admitted only after its unencrypted native task label
resolves exactly one accepted row in the ready isolated plan. The hook leaves
the ciphertext unchanged, stages that row's one-use grant, and at
`SubagentStart` re-resolves the row, injects the immutable specialist prompt
with its content-free goal hash, and consumes the grant against the observed
child identity.

Plaintext Codex, Claude, and ZCode launches retain exact goal equality and the
v1 rewritten-task envelope. External-write rows remain undelegable. An opaque
workspace-write row is bounded to the already isolated Codex workspace rather
than attempting to reverse content-free resource hashes into paths.

The focused boundary passes 97 warning-strict tests. A real SQLite Store test
now drives a non-canary goal through Codex's observed
`PostToolUse`-before-`SubagentStart` callback order and proves grant
consumption, specialist load, worker identity, and completed delegation. The
product rollout parser accepts v2 goal-hash evidence without retaining the
goal, specialist prompt, encrypted message, child tools, or child result. Two
focused decision mutations are killed with unchanged source.

The complete named fast spine is green on source commit `552eb05` plus the
v2 canary assertion correction: 593 documentation files, 603 Ruff files, 636
warning-strict Python tests with six skips, 110 dashboard tests, and every
routing gate passed. Decision conformance passed its baseline and killed all
69 mutations with zero survivors or invalid results; source remained unchanged.

## Approach

1. Recognize only the bounded Codex encrypted-message shape and require one
   exact task-label-to-plan-row resolution before issuing a grant.
2. Preserve the host-owned ciphertext exactly; never combine plaintext
   replacement text with Codex's encrypted block.
3. Deliver a token-free v2 child context at `SubagentStart` containing the
   immutable specialist identity, prompt, work-unit identity, and persisted
   goal hash.
4. Consume the staged grant only against one unambiguous observed child
   lifecycle identity, then reconcile callback order idempotently.
5. Keep wrong labels, ambiguous traces, malformed opaque input, wrong
   plaintext goals, external writes, missing prompts, and stale grants closed.
6. Project only content-free goal-hash and lifecycle evidence through product
   grading.

## Dependencies

AR-207 owns the product execution path that exposed this boundary. AR-203 owns
workspace-write and exact product proof, while AR-204 owns the integrated
README story. ADR-0127 records the Codex-specific host contract.

## Acceptance

- [x] An arbitrary opaque Codex product row can reach native child start when
  its task label resolves exactly one persisted accepted assignment.
- [x] The v2 child context binds the exact work-unit ID, goal hash, immutable
  specialist identity, and one observed child without retaining task content.
- [x] Wrong plaintext, malformed opaque input, and an unpersisted planned label
  fail closed.
- [x] A real Store regression proves the non-canary grant, load, worker, and
  completed-delegation lifecycle.
- [x] Product rollout evidence projects the v2 goal hash and excludes private
  task, prompt, tool, and result content.
- [x] Focused warning-strict tests and curated mutations pass.
- [x] The named fast verification spine passes.
- [ ] The reviewed repair is merged and exact-installed.
- [ ] One fresh exact-build activation and one product trial pass with zero
  corrections and proven workspace write.
