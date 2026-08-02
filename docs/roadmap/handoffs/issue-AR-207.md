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
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: d610630d4b3f8d04fc7cb2d0fc08fe6e19e44bbc
minimum_ledger_commit: d610630d4b3f8d04fc7cb2d0fc08fe6e19e44bbc
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` Exact installed
  `4d14b99` passes the named gate, canonical build, default Codex/ZCode/dashboard
  install, and one autonomous Codex activation with a valid first header and
  zero corrections.
- Writer sentinel `ar223-agency-writer-4d14b99-01` is consumed and terminal
  `NO-GO`. Its exact workspace is empty. Do not retry this build.
- The retained trial proves two defects: the product harness resolves exact
  activation by host plus prompt hash and collides with an older same-prompt
  route; inference also expands an explicit one-indivisible-unit request into
  five units, while the parent executes only onboarding and declines the rest.
- Direct app child `ar223-direct-native-child-01` independently proves current
  Codex child workspace-write capability. The remaining failure is Agency's
  exact evidence and inferred-plan contract, not OS workspace permission.
- Both defects are repaired locally without deterministic worker selection.
  Session plus prompt hash now resolves exact product evidence, and an explicit
  one-indivisible-unit request bounds the inference planner to one authored unit.
  The changed surface passes 127 warning-strict tests and Ruff.
- Clean repair `10c047f` passes the complete named gate: 657 Python passes with
  6 skips, 110 dashboard passes, every routing threshold, and 97/97 killed
  decision mutations with unchanged source. All documentation and Ruff gates pass.
- Exact `93e465a` builds and independently verifies; wheel SHA-256 is
  `6426f2e1e061a5b34f80aece547a0468e75f26a1d4a3667d2529dfa87df70d50`.
  Codex, ZCode, and the reachable dashboard install. Its one activation proves
  inferred/loaded/delegated `code-reviewer`, direct execution, a terminal
  exit-zero worker, accepted finalization, valid first header, zero corrections,
  and autonomous trust bypass without persistent profile change.
- Its one writer sentinel is consumed and `NO-GO`. Exact session resolution
  succeeds, but both Luna planner responses fail before routing. A single
  bounded direct-planner diagnostic reproduces the cause: Luna returns one
  schema-valid implementation unit, then deterministic completeness policy
  rejects it for three separate assurance units forbidden by the one-unit
  schema. Do not retry `93e465a`.
- Repair `73f9989` preserves the inference-owned one-unit plan through both
  policy checks while retaining external-write authorization. The focused
  workforce, intent, routing, and product-host slice passes 141 warning-strict
  tests; Ruff passes. Clean head `0f40e8e` passes the complete named gate: 657
  Python passes with 6 skips, 110 dashboard passes, every routing threshold, and
  97/97 killed decision mutations with unchanged source. No new live evidence
  has been consumed.
- `d610630` writer is consumed `NO-GO` at the separate-assurance contradiction;
  do not retry. Repair preserves one-unit staffing and clean head `62b7f3e`
  passes the complete named gate, including 97/97 killed mutations.
- Exact `7f0479f` builds and verifies; wheel SHA-256 is `e42ff9fa...f9186ef`.
  Its autonomous activation passes: session `019fc253-aedf-7822-9744-7911d5b37901`,
  trace `019fc253-bb0a-7f01-8927-ff2f945c76d2`, inferred/loaded/delegated
  `code-reviewer`, terminal worker, accepted finalization, valid first header,
  zero corrections, trust bypass without persistent change. Writer is unspent.

## completed-evidence

- The callback-order repair passes the complete named local gate: 37 activation
  and 52 execution/lifecycle tests; 657 Python tests with 6 skips; 110 dashboard
  tests; every routing threshold; repository-wide Ruff, formatting,
  documentation, metadata, policy, worklog, and diff checks. The full
  decision-conformance baseline passes and kills all 96 current mutations with
  zero survivors or invalid results and leaves source unchanged.
- Exact `4d14b99` builds canonically; wheel SHA-256 is
  `ad2bddce9bdd2f253ae3b2b15f44c70d4a481442af994269cf2fc0463334ff69`.
  Codex, ZCode, and the reachable dashboard install. Its autonomous activation,
  session `019fc1be-ef9a-7392-8eab-ecb196c40eb5`, trace
  `019fc1be-fbbf-70c3-b299-e47e16b19010`, proves one inferred/loaded/delegated
  `code-reviewer`, `spawn=1/followup=0/wait=1`, a dispatch receipt, terminal
  exit-zero worker, accepted finalization, valid first header, zero corrections,
  and trust bypass without persistent profile change.

## exact-blocker

Build, install, activation, and the named gate pass; one exact writer remains before dashboard/header proof. Writer
artifacts, concise header, dashboard parity, and the local report remain
unproven. The README story remains `NO-GO`.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Spend exact `7f0479f`'s one writer trial; stop on its terminal result.

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
  `ae322ec`, `bffd2c8`, `b6bcdfb`, `d4c65a7`, `4d14b99`, and `93e465a`
  consumed governed evidence;
  none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
