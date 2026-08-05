---
title: "AR-209: Bind opaque Codex child launches to exact plan rows"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [multi-harness, delegation, activation, product, security, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
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
v1 rewritten-task envelope. External-write rows remain undelegable. Preflight
now stages one bounded private Codex scope while it still has the transient
resource paths. Every later native-hook grant is checked against that immutable
scope: an exact file stays exact, and only the `repository-workspace` sentinel
maps to `.`. The private rows are absent from public evidence and are removed
when the parent turn terminalizes.

Opaque Codex launches are also serialized. The same tool-use ID can replay its
unconsumed grant idempotently, but a different plan row is denied until
`SubagentStart` consumes the first grant. The product scheduler therefore runs
one dependency-ready child at a time on this host. The exact-head review then
found two narrower defects: capability paths lost case on case-sensitive
repositories, and the slot guard also serialized plaintext token-correlated
Codex grants. The follow-up candidate preserves canonical path case while using
a separate folded contention key, and carries the actual opaque-launch decision
into the Store so plaintext grants may coexist.

The repaired changed surface passes 202 warning-strict tests, and the complete
Codex activation file passes 27 tests. Focused regressions prove the exact path,
immutable/terminal Store lifecycle, exact replay, second-spawn denial, and
post-consumption next-spawn admission. Both new decision mutations are killed
with unchanged source. The revised named fast spine is green through 594 docs,
604 Ruff files, 636 warning-strict Python tests with six skips, 110 dashboard
tests, and every routing gate. Decision conformance passed its baseline, killed
all 71 mutations with zero survivors or invalid results, and proved the source
tree unchanged. The follow-up six-node focused boundary and all 28 activation
tests pass. Its first 73-mutation attempt timed out at the 90-second baseline
before any mutation ran. AR-210 repaired that aggregate timeout mismatch; the
default rerun passed its 169.176-second baseline, killed all 73 mutations with
zero survivors or invalid results, and left source unchanged. The exact local
merge spine passes 595 docs, 604 Ruff files, 638 warning-strict Python tests
with six skips, 110 dashboard tests, and every isolated routing gate.

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
5. Persist exact preflight-derived path authority privately and verify every
   opaque Codex native-hook grant against it.
6. Serialize opaque launches until the prior grant is consumed at child start.
7. Keep wrong labels, ambiguous traces, malformed opaque input, wrong
   plaintext goals, external writes, missing prompts, and stale grants closed.
8. Project only content-free goal-hash and lifecycle evidence through product
   grading.

## Dependencies

AR-207 owns the product execution path that exposed this boundary. AR-203 owns
workspace-write and exact product proof, while AR-204 owns the integrated
README story. ADR-0128 supersedes ADR-0127 with exact private path authority and
serialized opaque launch semantics.

## Acceptance

- [x] An arbitrary opaque Codex product row can reach native child start when
  its task label resolves exactly one persisted accepted assignment.
- [x] The v2 child context binds the exact work-unit ID, goal hash, immutable
  specialist identity, and one observed child without retaining task content.
- [ ] ZCode/claude: Agent-tool child launches bind to exact plan rows with the
  same v2 child context.
- [ ] hermes/openclaw: BaseAdapter child launches bind to exact plan rows with
  the same v2 child context.
- [x] Wrong plaintext, malformed opaque input, and an unpersisted planned label
  fail closed.
- [x] A real Store regression proves the non-canary grant, load, worker, and
  completed-delegation lifecycle.
- [x] Product rollout evidence projects the v2 goal hash and excludes private
  task, prompt, tool, and result content.
- [x] Exact file-specific path authority is staged atomically with ready state,
  cannot be broadened or removed while active, and is cleaned at terminal state.
- [x] A second opaque grant fails until `SubagentStart` consumes the first;
  exact same-tool replay remains idempotent.
- [x] Mixed-case canonical paths survive preflight and grant construction
  unchanged while contention comparison remains conservative.
- [x] Plaintext token-correlated Codex grants can coexist; only opaque
  token-free launches use the single-slot guard.
- [x] Focused warning-strict tests and curated mutations pass.
- [ ] The post-review named fast verification spine passes.
- [ ] **codex**: The reviewed repair is merged and exact-installed.
- [ ] **zcode**: The reviewed repair is merged and exact-installed.
- [ ] **claude**: The reviewed repair is merged and exact-installed.
- [ ] **hermes**: The reviewed repair is merged and exact-installed.
- [ ] **openclaw**: The reviewed repair is merged and exact-installed.
- [ ] **codex**: One fresh exact-build product trial passes with zero corrections.
- [ ] **zcode**: One fresh exact-build product trial passes with zero corrections.
- [ ] **claude**: One fresh exact-build product trial passes with zero corrections.
- [ ] **hermes**: One fresh exact-build product trial passes with zero corrections.
- [ ] **openclaw**: One fresh exact-build product trial passes with zero corrections.

## Harness scope

This issue's concept applies across all supported execution hosts (codex,
claude, zcode, hermes, openclaw). The shared code path lives in the plan-row
grant and v2 child-context construction that binds every launch to an exact
persisted assignment, while the opaque-launch hook is host-specific:
`agency_runtime/adapters/hooks.py` (codex/claude/zcode via HookBridge) and
`agency_runtime/adapters/base.py` (hermes/openclaw via BaseAdapter). Each
host's live-trial checkbox above is independent.
