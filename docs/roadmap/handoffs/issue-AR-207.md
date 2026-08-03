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
  - docs/decisions/0145-place-exact-codex-execution-after-specialist-expertise.md
  - docs/decisions/0146-preserve-content-free-codex-child-tool-outcomes.md
  - docs/decisions/0148-classify-nested-codex-exec-tools-without-content.md
  - docs/decisions/0149-classify-codex-wrapper-failures-without-content.md
  - docs/decisions/0151-route-codex-product-approvals-to-auto-review.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: 8e74d56b39b20a4358d3b5b2500dd941da4e51d0
minimum_ledger_commit: 8e74d56b39b20a4358d3b5b2500dd941da4e51d0
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- Exact candidate `8e74d56b39b20a4358d3b5b2500dd941da4e51d0` builds canonically
  from a detached source tree and independently verifies. Wheel SHA-256 is
  `08faa80e1cbfb7ab0f98fa4c51562f544b18d3b7e9ac48fe7a9f31e466f2aad0`;
  source SHA-256 is
  `d9e41020f79249c1b7a916ce64bc2b3607b6b17cba4c15880a93b920902a703e`.
- The exact wheel is installed by immutable path. Full-suite install detects
  only Codex and ZCode, configures both, and leaves the dashboard active and
  reachable. The initial partial result is solely expected activation state.
- One autonomous activation passes with inferred `code-reviewer`, one completed
  child, accepted finalization, a valid first header, zero corrections, trust
  bypass, and no persistent trust mutation.
- Sole writer `ar223-agency-writer-8e74d56-01` passes with inferred
  `minimal-change-engineer`, exactly one completed child, two successful patch
  receipts, accepted finalization, a valid first header, zero corrections, and
  exact retained 23-byte workspace proof. AR-223 is complete.

## completed-evidence

- Activation session `019fc579-f916-7630-90cb-2157727164dd`, trace
  `019fc57a-0efb-74d0-a414-387fab76e38f`, run
  `0ed55d91-6ab6-4fdb-b761-6d5ac85e351f`, and delegation
  `e3ce9948-dc35-46e5-bb0c-fc73e29e063b` retain the activation pass.
- Writer session `019fc57d-f7ef-7721-9299-658529879311`, trace
  `019fc57d-f85f-7ed3-9ee5-29c1134adf78`, run
  `e49d2b57-2e18-4f63-b668-d88fcaba2183`, delegation
  `867595fe-a025-4107-914e-ca3c19887e76`, worker
  `019fc57e-a31b-7273-96ae-5ce30d16d1b1`, and finalization
  `0b7cf50b-58be-4da0-8d90-cab7c2eec8c7` retain the writer pass.

## exact-blocker

None for AR-223. The immutable installed product now proves autonomous
activation and real Agency child workspace execution with zero corrections.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

Resume the README umbrella through AR-203 and AR-204 using the now-proven
installed writer boundary. Freeze that package around the next missing visible
README scenario, retain one trial per exact build, and fail any correction
count greater than zero.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests/test_codex_activation_canary.py -q -W error
python -m pytest tests/test_native_child_lifecycle.py tests/test_product_host.py -q -W error
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
  `d610630`, `7f0479f`, `be1ca0e`, `d5a4e31`, `c8a0577`, `4c57507`,
  `2bbd885`, and `b967ad2` consumed governed evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
