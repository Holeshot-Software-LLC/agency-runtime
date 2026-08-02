---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-08-02
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-211-bound-immutable-commit-resolution.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/issue-AR-216-preserve-required-product-scenario-files.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/analysis/2026-07-31-ar-212-readme-story-evidence.html
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0133-treat-product-specialist-loads-as-turn-scoped.md
  - docs/decisions/0134-bind-contractor-risk-to-validated-authority.md
  - docs/decisions/0135-require-explicit-codex-child-execution-turns.md
  - docs/decisions/0136-bind-opaque-codex-execution-by-ciphertext-identity.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/decisions/0140-use-codex-stable-multi-agent-feature.md
  - docs/decisions/0141-admit-writer-proof-only-through-agency-plans.md
  - docs/decisions/0142-require-terminal-product-child-before-next-unit.md
  - docs/decisions/0143-execute-codex-specialists-in-the-initial-spawn-turn.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: bffd2c8f172ea774353158d10ad615a89c3d0095
minimum_ledger_commit: bffd2c8f172ea774353158d10ad615a89c3d0095
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` Exact installed
  `bffd2c8` passes the named gate, build, default suite install, and Codex
  activation. ZCode is enabled; the dashboard is active and reachable.
- The older consumed product `ar223-eb8e077-readme-01` proves nine inferred
  units, seven loaded specialists, nine completed workers, a valid first
  header, and zero corrections, but no writer artifact.
- Direct app child `ar223-direct-native-child-01` independently proves exact
  current-host child workspace-write. Generic Agency-disabled controls remain
  non-admissible under ADR-0141.
- Corrected writer sentinel `ar223-agency-writer-bffd2c8-01` is consumed and
  terminal `NO-GO`. It infers four units, launches and loads
  `minimal-change-engineer`, reaches terminal activation and execution waits,
  closes that worker at exit zero, and records zero corrections. It then
  truthfully finalizes `delegation_declined`; the other three accepted rows
  remain suggested and the exact workspace is empty.
- ADR-0143 removes the self-imposed two-turn Codex ceremony. Current direct
  delivery executes the exact persisted goal in the initial spawn turn, waits
  for terminal completion, and sends no execution follow-up. Historical V1/V2
  evidence remains readable only for retained trials.

## completed-evidence

- Exact `ae322ec` passes 657 Python production tests with 6 skips, 110 dashboard
  tests, every routing threshold, and 91/91 decision mutations. Its wheel and
  source archive pass strict metadata and independent exact-commit verification.
- Default installation discovers Codex and ZCode, installs both plus the
  dashboard, and records `trust_mode=autonomous_bypass`. Activation proves one
  inferred/loaded `code-reviewer`, one native worker, one accepted finalization,
  and zero corrections.
- The ADR-0142 focused slice passes 42 tests and both new decision mutations;
  the second and final surrounding lifecycle review passes 164 tests. Targeted
  Ruff passes. Clean head `a5b9d4b` passes the named gate: 657 Python tests
  with 6 skips, 110 dashboard tests, every routing threshold, and 93/93
  decision mutations with zero survivors or invalid results.
- Exact `bffd2c8` builds and installs with wheel SHA-256
  `1bf175f209969d773c4725a34ec70c6dace932b28304113a78d31eaf2e227aae`.
  Its default suite and autonomous activation pass with one inferred/loaded
  specialist, one completed worker, one accepted finalization, a valid first
  header, zero corrections, and no persistent trust change.
- The callback-order repair passes the complete named local gate: 37 activation
  and 52 execution/lifecycle tests; 657 Python tests with 6 skips; 110 dashboard
  tests; every routing threshold; repository-wide Ruff, formatting,
  documentation, metadata, policy, worklog, and diff checks. The full
  decision-conformance baseline passes and kills all 96 current mutations with
  zero survivors or invalid results and leaves source unchanged.
- Exact `b6bcdfb` activation proves an inferred/loaded `code-reviewer`, direct
  `spawn=1/followup=0/wait=1`, zero corrections, and accepted finalization, but
  lacks the dispatch receipt and terminal worker. Its retained callback order
  motivated the locally green ADR-0144 repair.
- Clean `d4c65a7` builds and installs; wheel SHA-256 is
  `581263464509639f9ca4efd7e9b8aff29e755af68e0da428c4cf9d7fd1e41075`.
  Codex, ZCode, and dashboard installation pass. Its single activation fails
  before routing because `codex-subscription` returns no valid planner response.
  Session `019fc1a8-1217-70a0-83ca-bae1f67e008e`, trace
  `019fc1a8-1c0c-7193-861b-0d72f14b7fdc`; no correction or writer trial ran.
- A bounded 2026-08-02 09:01 UTC diagnostic uses that installed build's exact
  planner schema. Codex reports `gpt-5.6-luna` as account-visible, exits zero
  with a complete structured turn, and Agency parses the response. The consumed
  activation remains unclassified; the failure is not currently reproducible.

## exact-blocker

The README main story remains NO-GO. ADR-0144 is locally green and installed,
but `d4c65a7` was consumed by an unclassified planner transport failure before
routing. Current exact-schema inference is healthy, so one fresh immutable
candidate may attempt activation. Product artifacts, concise header, dashboard
parity, and final report remain unproven.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Build and install one fresh exact candidate without changing the already
   gated runtime, then consume its one permitted autonomous activation.
2. Only an activation pass admits one Agency writer sentinel, exact file proof,
   and zero corrections.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_workforce_inference.py tests/test_workforce_dynamic_hiring.py -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
.venv\Scripts\agency.exe eval routing --json --no-details
.venv\Scripts\agency.exe eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Product host remains sandboxed to the exact trial workspace.
- Only Codex, ZCode, and dashboard are in machine scope.
- One live product trial per exact installed build; any correction is failure.
- Exact builds `e62d0adc`, `1694d6e`, `d6ba36a`, `9c2e9f8`, `8cfd975`,
  `f8e607d`, `386afca`, `5c45f154`, `ff39761`, and `43870c8` consumed governed
  live evidence; exact `ba76ce7`, `a2d1a7c`, and `5ff4a08` also consumed their
  activations; exact `b2be077` consumed both activation and product evidence;
  `ae322ec`, `bffd2c8`, `b6bcdfb`, and `d4c65a7` consumed governed evidence;
  none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
