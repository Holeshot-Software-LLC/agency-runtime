---
title: "AR-223: Prove Codex child task execution"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, codex, delegation, execution, evidence]
related:
  - README.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_host.py
  - tests/test_product_host.py
  - tests/test_codex_activation_canary.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-223
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/228
depends_on: [AR-221]
blocks: [AR-203, AR-204]
---

# AR-223: Prove Codex child task execution

## Problem

Exact merged build `43870c8b3052c1b274de396576a399b2cb542e61`
passes autonomous Codex activation with one inferred specialist, one real native
child, a valid first header, and zero corrections. Its one governed product
trial also accepts eight inference-authored units, applies one new live
contractor hire, launches eight distinct native children, projects every
current Codex wait, preserves every verified mutation scope, and accepts the
Store finalization.

The isolated product workspace nevertheless remains empty. The exact
`python-application-engineer` child goal contains the expected product request,
workspace-write proof path and token, `mutation_scope=workspace_write`, and a
hash matching the persisted plan. Codex records the child as completed even
though it does not create the mandatory first-write sentinel or any application
artifact. A native child completion therefore proves that a turn ended, not
that the spawn message became an actionable task.

## Current state

Trial `ar221-43870c8-readme-01` is consumed and terminal `NO-GO`. Session
`019fbe61-6267-7581-ada8-44d157c989e4`, trace
`019fbe61-62eb-7193-8ffd-e6f702c5271e`, run
`8c16f792-6941-4e54-b41b-ee4594976953`, route
`8d0ea8e3-9aef-40dd-9c1c-3a657510393c`, and finalization
`469f75a4-c422-4893-8a8d-ae0c604014ca` retain the exact Store boundary.
Correction count is zero and the first header is valid.

The inferred roster uses seven unique specialist identities across eight
units: `codebase-onboarding-engineer`, newly hired
`python-cli-architecture-specialist`, `python-application-engineer`,
`software-test-engineer`, `technical-writer`, `code-reviewer` twice, and
`test-results-analyzer`. The hiring case
`69bc7370-6763-4f41-966b-0b4af5215b54` is applied. All eight native child runs
have exit code zero, while the product report fails only
`workspace_write_not_proven` with `proof_file_missing`; independent validation
is correctly skipped because no artifacts exist.

The parent rollout contains eight spawns, eight waits, eight completed
children, zero failed children, zero timed-out waits, and zero unexpected
items. It records twenty-nine child tool calls but no content-bearing child
result. The current projector promotes every terminal child turn to a passed
worker outcome. Codex CLI 0.146.0 source defines `followup_task` as an explicit
turn-triggering message to an existing child, while the initial V2 spawn path
delivers an inter-agent communication that can be acknowledged without work.

The bounded local repair now separates those two lifecycle facts. Every
accepted Codex row stages an exact goal-hash-bound execution envelope, uses the
canonical `spawn_agent` → `wait_agent` → `followup_task` → `wait_agent`
sequence, claims the follow-up once in schema v43, and accepts a worker only
when its own bounded child rollout proves that exact envelope inside the second
terminal turn. The first readiness completion remains non-terminal for worker
evidence. Two bounded review passes have no unresolved High or Critical
finding. Three terminal focused slices pass 106, 176, and 36 tests respectively
(318 total) with warning-strict execution; the earlier combined invocation hit
its 304-second command timeout and is deliberately not counted. The named
Python production spine passes 656 tests with 6 skipped, dashboard UI passes
110 tests, documentation and Ruff gates pass, routing passes every threshold,
and decision conformance kills 84 of 84 mutations with zero survivors or
invalid results and unchanged source. Immutable-build live proof remains
pending. PR 229 merged exact
`ba76ce798b19b2e5306ef2d3ee09424c4246d07e`; the immutable upgrade planner
installed that exact VCS revision. Bare full-suite installation then refreshed
Codex and ZCode and restarted the dashboard: the dashboard is active and
reachable, ZCode is registered and enabled, and Codex is registered with the
expected `activation_required` state.

Its one autonomous activation canary is consumed and terminal `NO-GO`.
Session `019fbf1b-e062-7533-aaaa-bdde81cc2bae`, trace
`019fbf1b-f4a4-7d03-882e-25c90df4dadd`, run
`a94a6f82-561b-4784-8775-0a7e889ce2dd`, route
`94072e54-72b4-41de-b453-34b7d6141012`, and finalization
`37773104-d977-45da-af20-65db1d8c65ef` retain the exact boundary. Inference
selects `code-reviewer`, and the parent records one spawn, one completed
activation wait, and one `followup_task`. Agency's own `PreToolUse` hook rejects
that generated follow-up before the Store execution claim; therefore no second
wait or execution turn exists, the header is absent, and collaboration reports
`parent_wait_ambiguous`. Correction count is zero and persistent trust remains
unchanged. No product trial was launched.

The exact failure is now reproduced locally. Current Codex exposes the
`followup_task` message to `PreToolUse` and the parent rollout as a 760-character
`gAAAA...` ciphertext, while the receiving child alone sees the decrypted
canonical envelope. The repaired hook binds that opaque call to the unique
activated canonical child path and one-use Store claim. Activation and product
projectors likewise treat parent ciphertext as lifecycle evidence and still
require the exact decrypted envelope in the child's causal second turn before
accepting work. Exact local head `4daf82a` passes 143 focused hook, Store,
activation, and product tests; the named Python spine passes 656 with 6 skipped;
dashboard UI passes 110; documentation validates 625 files; Ruff, format, diff,
and every routing threshold pass. Decision conformance passes its 209.170-second
baseline and kills 84 of 84 mutations with zero invalid results and unchanged
source in 857.9 seconds. PR 230 merged that repair as exact
`a2d1a7c88f04956be0915c4b9acc4a21c5baf28c`. The immutable upgrade installed
that exact VCS commit, and `direct_url.json` independently reports the same
requested revision and commit ID. A subsequent full-suite refresh reports the
dashboard installed, active, and reachable; ZCode registered, enabled, and
complete; and the Codex bundle registered and byte-current. The install exits
partial only because Codex correctly remains `activation_required` until its
live canary runs.

That one activation is now consumed and terminal `NO-GO`. Session
`019fbf55-a690-7c20-804c-543def40a117`, trace
`019fbf55-b2dd-7602-90d7-7712854c752f`, run
`9d482344-0d67-42fc-8e49-52263b648a8b`, route
`3528a1c0-eaf9-4a4f-aed3-86a8a7eec27b`, finalization
`632849e2-5c42-4fa9-b58a-8773e75f96c4`, and child
`019fbf56-82e2-77d1-925a-43c5fcd19cbf` retain the exact boundary. Inference
selects `code-reviewer`; the parent records one spawn, two completed waits, one
accepted opaque follow-up, and one Store execution dispatch; the child completes
its second turn with the expected review response; and Store finalization is
accepted. Correction count is zero and persistent trust is unchanged.

Current Codex also persists the child's incoming execution message as a
760-character ciphertext with an empty visible payload. The model executes the
decrypted task, but the projector cannot reconstruct the exact envelope from
the persisted child rollout, so it reports `native_collaboration_topology_invalid`
and withholds the header. No product trial ran. The next proof boundary must
persist a content-free child-side receipt while the decrypted envelope is
available and cross-check it against the parent's one-use dispatch.

## Approach

1. Freeze child completion as lifecycle evidence only; never treat it alone as
   proof that the assigned work unit executed.
2. Adapt the product parent protocol to the current Codex V2 actionable-task
   boundary without permitting retries or duplicate work. Bind the one
   actionable delivery to the exact spawned child, native task name, work-unit
   ID, decoded goal hash, and accepted plan row.
3. Require a causal terminal child completion after that delivery. Reject
   missing, duplicate, reordered, cross-child, malformed, or unbounded task
   messages without retaining task or response content.
4. Preserve one-at-a-time dependency scheduling, the non-working parent,
   turn-scoped specialist authority, and the first workspace-write sentinel.
5. Run at most two reviews and the named local fast gate, then spend one fresh
   immutable-build activation and at most one product trial.

## Dependencies

AR-221 proves that current waits, exact goal delivery, verified mutation scope,
and workspace proof obligations reach every child. AR-219 owns exact multi-unit
topology evidence. ADR-0116 requires a real delegated workspace write,
ADR-0124 grades the inferred unit graph, and ADR-0128 binds opaque launches to
accepted plan authority.

## Acceptance

- [x] A terminal spawn turn is lifecycle evidence only and cannot by itself
  produce a passed worker outcome.
- [x] Every accepted plan row receives exactly one actionable native task on
  its exact spawned child, with no retry or duplicate execution path.
- [x] The actionable delivery and its later completion are proven causally and
  content-free against the exact unit ID, task name, child identity, and goal
  hash; all malformed variants fail closed.
- [ ] Read-only children and the parent cannot mutate the workspace; the first
  workspace-write child creates the exact proof before any other mutation.
- [x] Focused checks, at most two review passes, and the named local fast gate
  pass on one exact head.
- [ ] One new exact build passes autonomous activation and one fresh product
  trial with real specialist-created artifacts, independent checks, a valid
  first header, and zero corrections.
