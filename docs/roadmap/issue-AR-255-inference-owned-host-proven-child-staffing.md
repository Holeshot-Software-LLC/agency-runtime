---
title: "AR-255: Make native child staffing inference-owned and host-proven"
status: open
category: roadmap
created: 2026-08-12
updated: 2026-08-16
tags: [routing, inference, native-child, codex, evidence, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/codex_spawn_provenance.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/child_delivery_evidence.py
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-255
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-119, AR-180, AR-252, AR-253]
---

# AR-255: Make native child staffing inference-owned and host-proven

## Problem

The current JIT hook pre-narrows and compatibility-selects child cards in
deterministic local code, including a fail-open branch that can deliver every
candidate. That violates ADR-0118. Separately, the Codex canary can treat an
Agency-authored `specialist_load` row as card-delivery proof even though the
authoritative evidence contract requires an artifact written by the host.

The observed Codex Sol path exposes model-authored plaintext `task_name`, but
its `message` was encrypted and opaque to the hook. Codex 0.147 also has a
conditional plaintext path marked in the host response item, while that marker
is absent from the documented hook payload. Neither an unvalidated label nor a
plaintext-looking message is authority; the persisted exact host call must be.

## Current state

Runtime checkpoint `7e1b3603` makes inference the only native-child staffing
authority, preserves a valid multi-card result exactly, and fails open unstaffed
when inference is absent or invalid. It also collects Claude's canonical child
artifact inside an allocator-sealed disposable profile and current invocation
window, then passes a sealed one-use capability to canary evaluation. Store
rows, backend mappings, CLI input, caller-created roots, stale copies, and
replays cannot mint that capability.

Implementation and simulation are proven, not installed or live behavior. The
SafeClaude integration uses a test-managed install and fake process runner.
Claude's three prior-candidate artifacts remain historical context only.
Candidate `211563c7` correctly leaves unmarked calls unstaffed, preserves the
exact CLI `0.147.0` TUI/exec profiles, and adds a separate sealed Desktop
`0.147.0-alpha.6.6` profile for its observed root/depth-one/depth-two V2
ancestry. Scoped tests, mutations, authentic probes, and independent reattack
pass, so Codex Rule-4 Implementation and Simulation are proven. Exec depth-two/
deeper is unobserved and must remain fail open. Exact-install and live proof
remain open.

## Approach

Carry a validated inference decision to the native spawn boundary without
restoring Job B or allowing deterministic code to choose workers. Deterministic
logic may filter hard-ineligible cards, validate hashes and compatibility, and
reject invalid output; it may not rank or replace the inference result. If no
valid inference survives, deliver no card and emit an honest diagnostic.

Make the host-authored child artifact the sole green Rule-4 authority. Agency
Store rows may index or diagnose correlation but cannot prove delivery. For
Codex, accept a plaintext rewrite only after bounded canonical host-transcript
records match the exact session, turn, tool call, namespace, arguments,
current-call empty encrypted-argument marker, and any required cross-file causal
ancestry. Treat the documented transcript instability as versioned input and
fail open unstaffed on drift. AR-180 exact-installs and live-proves that channel
after source and adversarial simulation pass.
ADR-0159 governs this authorization boundary and its fail-open behavior.

## Dependencies

- ADR-0118 is the selection authority.
- `child_delivery_evidence.py` is the evidence-authority starting point.
- AR-209 is historical provenance for the retired plan-row transport and must
  not be restored as the fix.

## Checkpoint evidence

- Runtime `7e1b3603` and ledger `fb650b04` contain the implementation and its
  required traceability record.
- The final AR-255 focused package passed 229 tests with 1 skipped. The named
  fast Python production spine passed 673 with 6 skipped, dashboard UI passed
  134, and documentation validation passed for 685 Markdown files.
- Ruff lint and format, policy availability, worklog consistency, metadata, and
  `git diff --check` passed.
- Two independent adversarial passes found and drove fixes for Store-only proof,
  caller-selected roots, same-candidate replay, isolated install identity, and
  stale copied artifacts. The final reattack reported no unresolved Critical or
  High finding; its focused child-evidence suite passed 54 tests.
- Same-process private reflection and same-account transcript plus Store
  forgery remain the documented threat-model exclusion. No installed or live
  host layer advances from this checkpoint.
- The AR-180 read-only preflight identified exact Codex `0.147.0` and Desktop
  runtime `0.147.0-alpha.6.6` binaries, proved the current Sol/TUI spawn remained
  encrypted, and located a conditional host-marked plaintext path in the tagged
  `0.147.0` source. It did not run an Agency canary or change installation or
  trust state.
- Codex source `966845cc` and ledger `d9ee4a0a` add the sealed bounded scanner,
  double hook revalidation, and atomic replay guard. The 303-test focused slice,
  673-test fast spine with 6 skipped, 134 dashboard tests, Ruff, routing eval,
  and whitespace checks passed. Independent attack and the current-candidate
  mutation run remain open; Installed and Live layers do not advance.
- Independent attack found one Rule-4 completeness defect in nested rollout
  identity and one evidence-integrity defect in post-persistence drift cleanup.
  Repair `2fe5e9ec` and ledger `9eb6c683` address both with exact TUI/exec
  ancestry and transactional rollback. Its focused 206-test slice, Ruff, format,
  and whitespace checks pass.
- Hardening `e8b60f64` and ledger `4026ddd6` close the subsequent exact-schema,
  duplicate-identity, Store-projection, retry, and cleanup findings. The current
  342-test focused slice, 112/112 mutation run, 673-test fast spine with 6 skips,
  134 dashboard tests, routing gates, and independent review pass. Installed and
  Live layers remain unproven.
- Cross-file hardening `45b21cdc` and ledger `01730614` authenticate authentic
  one-record TUI ancestry across unique bounded canonical parent/root files.
  The census resolves 11/11 chains across depth-one sparse/inherited and depth-
  two sparse/inherited variants; the largest seals 48,678,898 external bytes and
  resolves in 3.809 seconds. The parent passed 365 focused tests, the 673-test
  fast spine with 6 skips, and 19/19 scoped mutations with a green baseline and
  unchanged source. The independent reviewer passed 200 tests, killed 19/19,
  and found no issue at any severity. The 134-test dashboard suite, routing,
  Ruff, format, and documentation/schema gates pass. The complete current
  decision-conformance evaluator exited zero in 883.1 seconds: baseline passed
  in 169,548 ms, all 131/131 mutations were killed, zero survived or were
  invalid, and `source_unchanged=true`. Installed and Live layers do not advance.
- Desktop hardening `211563c7` and ledger `ee8db873` add the sealed v3 profile
  pinned only to runtime `0.147.0-alpha.6.6`; the CLI profiles are unchanged.
  Desktop accepts one exact root and only 13 atomic observed depth-one/depth-two
  child tuples, rejecting eight tested unobserved cross-products. It requires
  V2 lineage, canonical owner files, both depth-two causal edges, adjacent direct event and
  output, sealed copied history/files/profile/currentness, the 64 MiB aggregate
  external bound, and the exact empty marker on the current call. Disabled
  guardians, greater depth, mixed profiles, and drift fail open unstaffed.
  Focused provenance/hook verification passed 288/288, focused plus the anchor
  passed 289/289, and the fast spine passed 673 with 6 skips. The Desktop
  baseline passed and killed 20/20 mutations with zero survived or invalid and
  `source_unchanged=true`; independent verification reproduced those results
  and found no issue at any severity. A content-safe authentic probe resolved
  52/52 V2 chains (47 depth one, 5 depth two), with maximum external ancestry
  32,650,955 bytes and maximum resolver time 2.765 seconds. All 65 observed
  Desktop calls were encrypted and unmarked, so State, Installed, and Live do
  not advance. For `211563c7`, dashboard UI passed 134/134, routing passed every
  threshold, and Ruff lint/format passed. The expanded decision-conformance
  evaluator remains pending; the 131/131 result above remains candidate-
  `45b21cdc` history.
- **2026-08-16, confirmed live cause of `native_child_inference_invalid`.** The
  first canary to complete on `980eb2d1b755` staffed the parent twice
  (`code-reviewer`, confidence 0.9 and 1.0) but failed every one of seven child
  routings, so no card ever reached a child and the collector reported
  `delivery_marker_absent`. **The children were not failing inference — they
  were abstaining, and the runtime records a sanctioned abstention as an invalid
  decision.** `build_judge_prompt` tells the model to "Select zero to 3
  specialists" and to "Return an empty selected_ids list when none fits";
  `validated_decision` accepts that empty answer, bounding only
  `len(selected) > max_sel`, and `applied_result` returns
  `status="applied"` carrying the model's own confidence; then
  `native_child_staffing` requires `1 <= len(selected)` and rejects the same
  answer as `native_child_inference_invalid`. Three layers, two contracts.
- **How the live rows prove it, without new instrumentation.** Every judge
  failure path hardcodes `confidence: 0.0`, and only `applied_result` preserves
  a model confidence, so the seven rows carrying **0.95, 0.95, 0.95, 0.95, 0.95,
  0.9 and 0.85** prove the judge returned `status="applied"` with
  `inference_mode="inferred"`. That excludes the status branch and the
  provider-receipt branch (distinct reason code), and `candidate_count: 33`
  excludes both early non-mapping branches, which record 0. Only the
  `selected_ids` check remains, and four of its five disjuncts — non-list,
  over-budget, unknown id, duplicate — are already enforced upstream by
  `validated_decision` over the same catalog using the same `agent_identity`
  function. The lower bound is the one disjunct nothing upstream enforces.
  Reproduced offline: an empty answer is the only case that the protocol accepts
  and staffing then rejects with the model's confidence intact.
- **Two projection fields are structurally constant on this path and must not be
  read as evidence.** `_unstaffed` always writes `selected_ids: []`, and the
  complete-universe judge always passes `top_score=0.0`. Neither reflects what
  the model returned. `candidate_count: 33` is the eligible catalog after
  host/platform/tool filtering, against 283 in the full roster; the gap is
  expected filtering, not a defect.
- **This is a behaviour contract, not an oversight.**
  `test_invalid_duplicate_unknown_and_over_budget_inference_is_rejected_whole`
  parameterises `[]` alongside duplicate, unknown, and over-budget answers, so
  changing it renegotiates a written test contract. It is also **not** the same
  fault as the parent-side ranking failure: the parent recruiter has legitimate
  abstention outcomes (`recruiter_abstained`, `no_safe_sufficient_team`), while
  the child path collapses abstention into "invalid".
- **Still open: why the model declined seven times out of seven.** The failure
  row keeps only `source_message_hash`, so the child task text is unrecoverable
  from the Store, and `hooks.log` holds no row for the canary parent trace
  `3b304fbb`. A deliberate decline on a task whose parent had just selected
  `code-reviewer` is suspicious on its face, but nothing yet distinguishes "the
  child task genuinely needed nobody" from "the child prompt or catalog made
  every candidate look unfit". Giving abstention its own reason code is what
  makes that question answerable from evidence.

## Acceptance

- [x] Every delivered specialist slug and version is an exact member of one
      validated inference decision; deterministic code never chooses a worker.
- [x] A valid compatible multi-card inference decision reaches the child intact;
      deterministic code does not truncate it to one card.
- [x] No provider or no valid inference yields no Agency-supplied specialist,
      card, activation, or hire and records one explicit failure reason; the
      native host remains free to proceed unstaffed.
- [x] Canary success requires a host-written child artifact containing the
      exact card hashes before the child's first speech; Store-only rows fail.
- [x] Spoofed, replayed, stale, encrypted-but-unbound, or Agency-authored
      evidence cannot produce a green result.
- [ ] The Codex channel binds the inference decision, parent/child correlation,
      card hashes, and install identity; focused spoof, replay, stale, and
      opaque-label adversarial tests pass.
- [ ] Claude's three prior-candidate artifacts remain valid historical
      evidence, an exact-candidate host artifact turns its installed/live
      layers green, and the current projection rejects Store-only claims.
