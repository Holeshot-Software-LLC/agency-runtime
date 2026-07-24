---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [handoff, routing, workforce, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-119-green-main-then-finish
evidence_commit: c95ecea09c573cd46e5b10d196029234f411cd29
minimum_ledger_commit: c95ecea09c573cd46e5b10d196029234f411cd29
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

This is the bounded current-state projection for AR-119. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) remains
the complete acceptance contract.

## Checkpoint

- Branch: `codex/ar-119-green-main-then-finish` (from `origin/main`
  `effa10b`). Substantive/ledger head: `c95ecea`.
- Live umbrella [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132)
  remains open; tracker writes need authorization.
- Architecture pivoted to ADR-0087 (inference-decides-from-a-relevance-
  shortlist). The deterministic decider is removed from the runtime.

## Completed evidence

PR #129 merged red; Phase 0 recovery + the ADR-0087 pivot are underway.
Each below is verified green and ledgered.

- **P0a** `9d68e7e`: dashboard assets 275,892 B -> 240,565 B (21.1 KiB
  headroom). `.zcode` ignore `dc0d3f2`. **P0b** `10e3b4c`: Codex
  PreToolUse hook contract. **P0c** `45f78cc`: routing fixtures.
  **D1/D2** `8b95ab0`: roster opaque-hash tolerance + reroute-on-
  mismatch (the only genuine prod fixes). **P0e** `85cd7b7`: schema
  fixtures. Conflict-closure seeding `fb9829e`.
- **ADR-0087** `495b4a4`/`58c9cd9`: inference is the sole decider;
  deterministic recall stays as stage 1; offline declines; the upstream
  asset worth borrowing is the audited pool, not its selector.
- **Offline-decline pivot** `ee47985`: `plan_and_staff_workforce`
  returns a labeled `_declined_outcome` (no deterministic decider) when
  no provider is configured. 45 workforce-inference tests pass.
- **Invoker seam** `c95ecea`: `plan_and_staff_workforce(invoker=None)`
  resolves the module-global at call time, so the full
  preflight->route->workforce stack is stubbable via monkeypatch without
  a live CLI.

## Exact blocker

The inference funnel runs end-to-end against the real codex CLI
(codex-cli 0.145.0 is installed). Isolated testing of
`_recruit_ambiguous_plan` PROVES the model nominates correctly: for
"review code for correctness and security" it ranks
`codebase-onboarding-engineer` (required, 0.99) for codebase-discovery,
`code-reviewer` (acceptable) for code-review, etc. — exactly the right
specialists, correctly classified.

The nomination is then REJECTED by `_proposal_from_nominations` with
`workforce nominations have no safe team; ... status=agent_tools_missing
... missing=capability:repository-map`. Two compounding verifier gates
block a correct nomination:

1. **`agent_tools_missing`**: the verifier gates each candidate on
   `unit.required_tools` against the host's available tools. The isolated
   test passes `available_tools=frozenset()` (empty), so every specialist
   is "tools missing." In production the host supplies tools
   (repository-read, etc.); the gate is correct but the test context is
   empty. Production-path and tests that supply real tools should pass.
2. **`capability:repository-map`**: the deterministic plan still emits
   the bespoke capability `repository-map` (the reverted-WP1 vocabulary
   bug), which no contract has, so `missing=capability:repository-map`
   rejects otherwise-matching candidates. The capability derivation fix
   IS needed — derive from `artifact_kind` via `ARTIFACT_CAPABILITY`.

Also: the inference recruiter is currently gated as an optional
*refinement* (`mode != "fast"` + `_can_refine_with_recruiter`), not the
primary decider. Default `mode="fast"` + `fast_call_budget=1` means it
never runs. Making it primary (ADR-0087) cascades into 7 mode/budget
tests that encode the old refinement model and must convert.

## Next bounded work package

1. Re-apply the capability derivation (artifact_kind -> core id) —
   confirmed needed; this time keep it scoped and accept the
   `test_security_patch_review...` regression converts to the inference
   path (the decider no longer claims optimality).
2. Make the inference recruiter the primary decider when a provider is
   configured (run regardless of mode), and raise `fast_call_budget` so
   planner+recruiter fit. Convert the 7 mode/budget/cache tests.
3. Confirm end-to-end with real codex that a correct nomination is
   ACCEPTED (supply real tools in the context) and selects the best
   specialist; declare a gap -> hire on a FluxUI-style ask.
4. Then convert the 14 selection-asserting suites and resume green-main.

## Live-evaluation baseline (unchanged)

Two unchanged corpora produced 19/19 safe Agency passes; the newest
returned 17/19 (active-incident abstained on margin; accounts-payable
omitted the CFO review). No corpus has produced 19 benchmark-valid
upstream arms; malformed/timed-out/no-response arms are validity
failures, never losses.

## Same-task continuity

Context thresholds never create/fork/dispatch/wait for another task.
Continue through compaction. At or below 50%, ensure a clean durable
checkpoint, then continue in the same task.

## Verification

~~~text
.\.venv\Scripts\python.exe scripts\docs_metadata.py --check
.\.venv\Scripts\python.exe scripts\update_policy_availability.py --check
.\.venv\Scripts\python.exe scripts\update_worklog.py --check
.\.venv\Scripts\python.exe scripts\verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_inference.py -q -W error
git diff --check
.\.venv\Scripts\python.exe scripts\context_handoff_status.py --json --threshold 50
~~~

## Constraints

- Telemetry before every live evaluation; conservative estimate when
  `CODEX_THREAD_ID` is absent.
- Do not weaken typed coverage/parser validation, add a scenario route,
  reinterpret malformed upstream output, or claim Agency is better
  without a benchmark-valid comparison.
- A specialist governs its unit (generalize/test/review); offline
  declines rather than emit a keyword-luck pick (ADR-0087).
- Update the canonical issue and replace this capsule when the package
  changes; create the required substantive and ledger commits.
