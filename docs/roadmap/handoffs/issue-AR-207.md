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
evidence_commit: be1ca0e69652645f4bf5be7a48a81de47a869821
minimum_ledger_commit: be1ca0e69652645f4bf5be7a48a81de47a869821
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` Repair `260865e`
  makes accepted activation explicit tool and workspace proof for each native
  child; ledger `be1ca0e` is the clean candidate.
- The complete named gate passes: 657 Python tests with 6 skips, 110 dashboard
  tests, every routing threshold, 97/97 killed decision mutations with unchanged
  source, and every documentation, policy, Ruff, formatting, and diff check.
- Exact `be1ca0e69652645f4bf5be7a48a81de47a869821` builds canonically and
  independently verifies. Wheel SHA-256 is
  `c707342bfb4392d89ae5f07d202cd7a0e73d1a7dfc52304c5d16e2b53ad9f519`;
  source SHA-256 is
  `451c8a4286f1167d5f29788c3a415c47f979305b6172f038369b274e46a69dd1`.
- Codex, ZCode, and the reachable dashboard install. The one activation proves
  inferred/loaded/delegated `code-reviewer`, a terminal exit-zero worker,
  accepted finalization, valid first header, zero corrections, and autonomous
  trust bypass without persistent profile change.
- Writer `ar223-agency-writer-be1ca0e-01` is consumed `NO-GO` after 78.672s.
  Inference selects/loads/delegates `minimal-change-engineer`; one spawn and one
  wait complete exit zero; finalization and the first header pass with zero
  corrections. Independent inspection finds zero workspace entries, so
  `workspace_write_not_proven` is the sole failure. Do not retry `be1ca0e`.
- Direct child `ar223-direct-native-child-01` already proves current Codex child
  workspace-write capability. The explicit tool/workspace-proof hypothesis is
  falsified; the remaining defect is inside Agency's delivered specialist turn
  or its native execution boundary, not OS permission.
- Retained comparison proves both launches use `fork_turns=none`: the direct
  child records a successful workspace-local patch and byte verification while
  the Agency child records zero tool calls. Agency was accepting lifecycle and
  a nonblank final answer without a write receipt.
- The bounded local repair now requires a successful child-turn
  `patch_apply_end` entirely inside the exact workspace before a
  `workspace_write` row can record `ok`. One native `SubagentStop` continuation
  tells the child to execute; a repeated miss terminates, and parent-`Stop`
  applies the same receipt gate. Product/v3 instructions require the exact
  proof mutation without generic specialist expansion. Ninety-seven focused
  tests plus targeted Ruff/format/diff checks pass. No build has been consumed.

## completed-evidence

- Activation session `019fc29f-f8da-7360-8a1c-38cbe9a2f9fa`, trace
  `019fc2a0-0584-7f71-a1eb-a54ed8ebf098`, and worker
  `codex-agent:019fc2a0-f083-7712-a042-f70fed29bef8` retain the fresh pass.
- Writer session `019fc2a3-1b73-7162-a10b-ab2b891a7876`, trace
  `019fc2a3-1be8-7481-b08f-df6801a08964`, run
  `00ffae19-8b6c-4217-846d-a7dc2fc4dfb1`, and worker
  `codex-agent:019fc2a3-c2c3-7b32-b16e-f2dbb27d97ed` retain the failure.

## exact-blocker

Build, install, activation, routing, delegation, first header, and zero
corrections pass on consumed `be1ca0e`. Its delegated workspace execution
failed because Agency accepted a zero-tool child. The scoped receipt repair is
focused-green but unbuilt and not live-proven, so README remains `NO-GO` and
header/dashboard/report work remains deferred.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Commit this focused-green receipt repair and its ledger checkpoint.
2. Run the complete named local gate once.
3. If green, build/install one new immutable candidate, run one autonomous
   activation, and spend one fresh Agency writer proof. Stop at its first
   failure; do not broaden or retry the build.

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
  `d610630`, `7f0479f`, and `be1ca0e` consumed governed evidence;
  none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
