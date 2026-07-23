---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-23
tags: [handoff, routing, workforce, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-119-green-main-then-finish
evidence_commit: 25643ed59af997b4640b596c8ab5aba275a316dd
minimum_ledger_commit: 25643ed59af997b4640b596c8ab5aba275a316dd
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

This is the bounded current-state projection for AR-119. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) remains
the complete historical and acceptance contract.

## Checkpoint

- Branch: `codex/ar-119-green-main-then-finish` (fresh from `origin/main`
  `effa10b`; the prior `codex/ar-115-live-routing-trust` merged via
  PR #129 and is no longer active).
- Substantive/ledger head: `25643ed`.
- Live umbrella: issue
  [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132),
  still open. Tracker writes need explicit authorization.
- Phase 0 (green main) is in progress; live evaluation (Phase 1) is
  blocked until merged `main` CI is green.

## Completed evidence

PR #129 merged with red CI. Phase 0 (green main) recovery is underway on
`codex/ar-119-green-main-then-finish`; each item below is verified green
locally and recorded in the worklog.

- **P0a** `9d68e7e`: dashboard asset budget 275,892 B -> 240,565 B
  (21.1 KiB headroom under the fixed 256 KiB gate). 97 dashboard UI
  tests + 20 release/shard tests pass.
- **dc0d3f2**: ignore local `.zcode` editor state so `verify_docs` stops
  treating its plan Markdown as missing-front-matter docs.
- **P0b** `10e3b4c`: accept the `PreToolUse` hook in the Codex bundle
  contract (`smoke._CODEX_HOOK_EVENTS`). Unblocks both artifact-smoke
  jobs and ~17 marketplace-schema cases. `agency smoke --json` passes.
- **P0c** `45f78cc`: align selector fixtures with the traced workforce
  contract (`_RouteRequest.trace_id`/`workforce_catalog`,
  `routing_context_fingerprint`, state-aware greeting triviality). 76
  routing tests pass.

The static gate (`quality-contracts`) is green locally: ruff, format,
`test_ci_sharding` + `test_release_packaging`, and `dashboard_ui` all
pass; `verify_docs` passes (331 files).

## Exact blocker

Phase 0 must finish before merged `main` CI is green and Phase 1 can run.
Genuine production fixes (store/roster.py):
- **D1**: opaque upstream roster `content_hash` now hard-fails the
  workforce `version_hash` SHA-256 check; preserve opaque-identity
  tolerance (test: `test_roster_remediation`).
- **D2**: a tampered `agent_active.hash` raises from the snapshot reader
  instead of signalling stale/reroute to the continuation guard (test:
  `test_durable_continuation`).

Test-align (fixtures lag the PR-#129 contract):
- **D3/D4/D5/F3/F4**: fixtures activate only `code-reviewer`, whose
  `same_context_conflicts` target `codebase-onboarding-engineer` is now
  enforced by `workforce_index_fingerprint`. Seed the conflict closure.
- **D6**: code-reviewer projection now includes `quality-assurance`.
- **E1**: `MAX_SELECTED_SPECIALISTS` -> `MAX_DURABLE_SPECIALIST_REFERENCES`.
- **E2**: `_Result` mock must be iterable for the SCHEMA_VERSION 33->35
  path.
- **E3**: `_AttemptStore` needs workforce-snapshot stubs.
- **E4**: schema version 32 -> 35.
- **F1** `broker_token`; **F2** `_validate_installed_dashboard_launcher`;
  **F5** delegation unit-agent plan via `_activation_work_unit`;
  **F6** `ClaudeChildAssignment` -> `NativeChildAssignment` fixture
  rewrite; **F7** codex Stop uses `continue`/`stopReason` not `decision`;
  **F9** isolated-host abstention needs a `unit_agent_plan`;
  **F10** security-audit unit winner reorder.
- **F8** product validator: passes locally; likely CI interpreter/env.
  Confirm on the hosted run.

After P0d-P0f: run the full local suite + four shards, push, open the
green-main PR, and require hosted CI green before Phase 1.

## Live-evaluation baseline (unchanged, Phase 1)

Two unchanged complete corpora produced 19/19 safe Agency passes. The
newest complete corpus returned 17/19:
`active-incident-containment` abstained on `selection_margin_too_low`;
`accounts-payable-cfo-separated` omitted the required CFO review. Three
upstream arms returned unknown disabled shadows. No complete corpus has
produced 19 benchmark-valid upstream arms; malformed/timed-out/no-
response arms are validity failures, never losses.

Latest capture:
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-154100`.
Accepted 19/19 baseline:
`C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eb3-full-20260723-072402\stdout.json`.

## Next bounded work package

Finish Phase 0 green-main recovery: the two roster production fixes
(D1/D2) first, then the test-align cluster, then the full local suite +
shards. Only after merged `main` CI is green does Phase 1 resume with
the matched two-case confirmation for exactly:

~~~text
active-incident-containment
accounts-payable-cfo-separated
~~~

Keep every live control unchanged (Windows, roster 561, 272 governed
workers, 247-tool context, codex-subscription, gpt-5.6-luna, low effort,
one fast call, 15000 ms cold gate, no scenario routes). Telemetry before
every live run (conservative estimate when `CODEX_THREAD_ID` is absent).
If both cases pass, make no product change. If either repeats, compare
complete plans with prior accepted outcomes and fix only a genuinely
general defect.

## Same-task continuity

Context thresholds never create, fork, dispatch, or wait for another
task. Continue in the current task through normal compaction. At or below
50 percent, ensure a clean durable checkpoint, then continue in the same
task, including live evaluation.

## Verification

~~~text
.\.venv\Scripts\python.exe scripts\docs_metadata.py --check
.\.venv\Scripts\python.exe scripts\update_policy_availability.py --check
.\.venv\Scripts\python.exe scripts\update_worklog.py --check
.\.venv\Scripts\python.exe scripts\verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/ -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency smoke --json
git diff --check
.\.venv\Scripts\python.exe scripts\context_handoff_status.py --json --threshold 50
~~~

## Constraints

- Check telemetry immediately before every live evaluation; the reading
  only determines whether a clean checkpoint must first be ensured.
- At or below 50 percent, create a clean durable checkpoint and continue
  in the same task; never dispatch a task or wait for telemetry to reset.
- Preserve every accumulated AR-119 commit and the clean branch.
- Do not weaken typed coverage, add a scenario route, raise the 15000 ms
  gate, increase the one-call budget, or reinterpret malformed upstream
  output.
- Do not claim Agency is better without a benchmark-valid comparison and
  independently graded completed-outcome evidence.
- Do not mutate or close issue #132, or mark AR-119 complete, until every
  acceptance gate has current evidence; #132 closes last.
- Update the canonical issue and replace this capsule when the package
  changes; create the required substantive and ledger commits.
