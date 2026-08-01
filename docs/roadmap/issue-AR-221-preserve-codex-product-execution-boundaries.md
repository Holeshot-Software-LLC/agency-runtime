---
title: "AR-221: Preserve Codex product execution boundaries"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, codex, delegation, workspace, evidence]
related:
  - README.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_host.py
  - agency_runtime/core/workforce/routing_projection.py
  - tests/test_codex_activation_canary.py
  - tests/test_product_host.py
  - tests/test_ar214_context_delivery_authority.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-221
priority: p0
tracker_url: null
depends_on: [AR-219, AR-220]
blocks: [AR-203, AR-204]
---

# AR-221: Preserve Codex product execution boundaries

## Problem

Exact merged build `ff39761c48564f1ace92d346cbe45df64fb86114` passes
default Codex, ZCode, and dashboard installation and autonomous Codex
activation. Its one product trial accepts a seven-unit inference-authored team,
launches seven distinct native children, consumes every grant, completes every
delegation and worker with exit code zero, and accepts the Store finalization.

The product host nevertheless fails at two independent boundaries. First,
Codex accepts and completes a `wait_agent` call allowed by the current host
schema, whose bounded maximum is 3,600,000 milliseconds, while the product
rollout projector still rejects any value above 600,000 milliseconds. The
private numeric argument is intentionally not retained, but the exact terminal
diagnostic is `product_wait_arguments_invalid`; the activation canary's separate
exact 60,000-millisecond contract remains green and must not change.

Second, the isolated workspace remains empty. The accepted plan marks unit
`unit-34912a488e` as `workspace_write`, while its reconstructed exact child goal
ends only with `modify authority`. Its hash exactly matches the persisted
`34912a488e52525f5fb8709bcf0b7fbb0f3eb58000fc0fa708678403bf3c7643`.
The product proof instruction conditions its required first mutation on the
literal `mutation_scope=workspace_write`, but that verified value is absent from
the decoded goal. The child therefore receives the proof token without the
fact that makes it the responsible writer.

## Current state

Trial `ar220-ff39761-readme-01` is consumed and terminal `NO-GO`. Session
`019fbe0a-4e75-7bb0-a1e2-1a2a54e2415a`, trace
`019fbe0a-4f10-76d1-ba75-9e8615706dd0`, run
`28c98413-c312-41fa-be2d-33479b226090`, route
`6e4e32fe-92a2-41f5-b0d3-499d4e9b64a9`, and finalization
`8ecffcc4-7d17-40e9-a43b-1cf5ca039d2d` retain the exact Store boundary.
The route selected seven units and six unique specialist identities, reusing
`code-reviewer` once. All seven native children completed. Correction count is
zero, but the first header is absent because collaboration projection failed.

The collaboration diagnostic records seven spawns, seven waits, fourteen tool
outputs, seven child starts, twenty-three parent messages, zero unexpected
items, and `product_wait_arguments_invalid`. The workspace-write proof file and
all product artifacts are absent, so validation is correctly skipped. No hiring
case exists for this trace: the two contractor identities were existing roster
versions, not new hires, and AR-220's four-call repair remains live-unproven.

Exact local commit `adad73292ca2d741bf242f4da629bf9057352376` accepts product
waits through 3,600,000 milliseconds while leaving the activation canary
unchanged. Current descriptors and exact goals
now carry the verifier-accepted mutation scope. Goal construction reserves the
scope suffix under the 4,096-character ceiling, and every workspace-write child
checks the prompt-bound sentinel before its first mutation while other actors
remain prohibited. Two review passes are complete. The consolidated focused
slice passes 127 tests, and three independent curated mutations are killed with
zero survivors or invalid cases and unchanged source. AR-222 records seven
unrelated legacy integrity-test failures that are unchanged from `origin/main`.

## Approach

1. Bind the product-only wait validator to the current native host ceiling while
   preserving strict type, key, cardinality, and completion checks. Do not alter
   the activation canary's exact 60,000-millisecond contract.
2. Carry the inference-authored, verifier-accepted mutation scope into every
   reconstructed work-unit descriptor and exact decoded goal.
3. Make the product proof instruction self-assigning: a child whose exact goal
   says `mutation_scope=workspace_write` checks the sentinel before its first
   mutation, creates it only when absent, and otherwise leaves it unchanged.
   Read-only children and the parent remain prohibited from creating it.
4. Prove the exact product request, scope, proof token, unit ID, and goal hash
   survive route projection, plan hydration, and native child delivery without
   storing provider or child content in durable diagnostics.
5. Run two bounded reviews and the named local fast gate, then spend only one
   new immutable-build activation and at most one product trial.

## Dependencies

AR-219 owns exact multi-unit product evidence. AR-220 owns the locally repaired
hiring-critic path, which this consumed trial did not exercise. ADR-0116 requires
a real delegated workspace write, ADR-0124 grades the inferred unit graph, and
ADR-0128 binds every opaque Codex launch to exact plan authority.

## Acceptance

- [x] Product waits through the current 3,600,000-millisecond host ceiling are
  accepted; zero, booleans, unknown keys, and values above it fail closed.
- [x] The activation canary still requires exactly 60,000 milliseconds.
- [x] Every current workforce descriptor and child goal carries its exact
  verified mutation scope, and reconstruction preserves the exact goal hash.
- [x] The first workspace-write child has an unambiguous sentinel obligation;
  later writers, read-only children, and the parent cannot overwrite it.
- [x] Missing, malformed, preexisting, out-of-scope, or parent-authored write
  proof remains terminal failure.
- [ ] Focused checks, at most two review passes, and the named local fast gate
  pass on one exact head.
- [ ] One new exact build passes autonomous activation and one fresh product
  trial with real artifacts, independent checks, a valid first header, and zero
  corrections.
