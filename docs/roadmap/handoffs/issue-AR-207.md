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
evidence_commit: d5a4e3190a49b94b47620a98c4c313a0f1518d04
minimum_ledger_commit: d5a4e3190a49b94b47620a98c4c313a0f1518d04
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` Scoped repair
  `a854e8e` requires a successful local patch receipt before a
  `workspace_write` child can record success; ledger `d5a4e31` is consumed.
- The complete named gate passes: 657 Python tests with 6 skips, 110 dashboard
  tests, every routing threshold, 98/98 killed decision mutations with unchanged
  source, and every documentation, policy, Ruff, formatting, and diff check.
- Exact `d5a4e3190a49b94b47620a98c4c313a0f1518d04` builds canonically and
  independently verifies. Wheel SHA-256 is
  `c00a2317ea7db20512701602a7920216a824b8bdab9166eacfe8bb7e76dfa0f2`;
  source SHA-256 is
  `a58c47522306900189db5760a07dc199f61536336816e4529207804e01772d9f`.
- Codex, ZCode, and the reachable dashboard install. The one activation proves
  inferred/loaded/delegated `code-reviewer`, a terminal exit-zero worker,
  accepted finalization, valid first header, zero corrections, and autonomous
  trust bypass without persistent profile change.
- Writer `ar223-agency-writer-d5a4e31-01` is consumed `NO-GO` after 85.844s.
  Inference selects/loads/delegates `minimal-change-engineer`; projection shows
  one spawn, one wait, one completed child, zero corrections, and a valid first
  header. Receipt enforcement leaves the Store worker unended and delegation
  incomplete, but parent finalization still records `accept/completed` with no
  missing rows. Independent inspection finds zero workspace entries. Do not
  retry `d5a4e31`.
- The focused parent-finalization repair now requires every current v14
  `workspace_write` unit to have exactly one `completed` delegation with a
  terminal timestamp before acceptance. Missing, delegated-only,
  timestamp-free, duplicate, or malformed evidence fails closed as
  `delegation_execution`. The exact regressions pass; 264 adjacent tests pass
  with one platform skip. No new build or live trial has been consumed.

## completed-evidence

- Activation session `019fc2ef-4dbf-7a93-961d-8af333446b0c`, trace
  `019fc2ef-5984-7103-bf17-8c51acf3927e`, and worker
  `codex-agent:019fc2f0-4b31-71f1-beb9-ce135020b0d7` retain the fresh pass.
- Writer session `019fc2f2-63f6-7a62-af0b-bdd4dbe9124e`, trace
  `019fc2f2-6465-7df0-a093-621733808dab`, run
  `7b18905e-0621-497e-9f8c-7ec79486420b`, and worker
  `codex-agent:019fc2f3-1864-7840-b5d2-84edf35dd077` retain the failure.

## exact-blocker

Build, install, activation, routing, selection, delegation projection, first
header, and zero corrections pass on consumed `d5a4e31`. Receipt enforcement
prevents false worker completion, but parent finalization still accepts the run
with its writer delegation incomplete. The focused parent-finalization repair
is locally green but unbuilt. Workspace execution remains unproven, so README
remains `NO-GO` and unrelated surfaces stay deferred.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Commit the focused parent-finalization repair and its ledger checkpoint.
2. Run the complete named gate once. If green, build/install one new immutable
   candidate, run one activation, and spend one writer proof. Never retry
   `d5a4e31` or broaden the package.

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
  `ae322ec`, `bffd2c8`, `b6bcdfb`, `d4c65a7`, `4d14b99`, `93e465a`,
  `d610630`, `7f0479f`, `be1ca0e`, and `d5a4e31` consumed governed evidence;
  none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
