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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-223-post-merge-live-proof
evidence_commit: 95aec42db22b3b45ecb706c7fb2ada9f0ae3d181
minimum_ledger_commit: b967ad237d841e1ed37bb6e7312d82456b0aeab8
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` This stop-loss slice
  froze at Store v2 diagnostics plus one immutable activation/writer attempt.
- ADR-0148 implementation `95aec42` records content-free nested exec classes
  and fixed wrapper outcomes on each exact worker receipt. The 118-case focused
  slice, named 657-pass Python spine, 110 dashboard tests, docs/Ruff/format,
  routing thresholds, and isolated new mutation are green. The full conformance
  command completed but its oversized terminal JSON was not retained; it was
  not rerun under the stop-loss contract.
- Exact `b967ad237d841e1ed37bb6e7312d82456b0aeab8` builds canonically and
  independently verifies. Wheel SHA-256 is `1774977dfcd457ac832eba59a45e037dca97e265849dabf652200b59afaa09db`;
  source SHA-256 is `47c005a0f946d4617e09d8f544ecfc42e40a75c4aefec2bd33934e2e9f07f917`.
- The full-suite install refreshes Codex and ZCode and leaves the dashboard
  active and reachable. One autonomous activation passes without persistent
  trust mutation.
- Sole writer `ar223-agency-writer-b967ad2-01` is consumed `NO-GO`. Inference
  selects and loads `minimal-change-engineer`; one spawn and one completed wait,
  exact-workspace trust, hook bypass, a valid first header, and zero corrections
  pass. The workspace remains empty and finalization declines missing
  `delegation_execution`.
- Store v2 is recorded from the persisted rollout: all three exec inputs classify
  as one nested `apply_patch` and two nested shell calls; all three wrapper
  outcomes are `failed`, with zero unclassified or missing outputs.

## completed-evidence

- Activation session `019fc435-1a8c-7162-886f-389a168122ec` and trace
  `019fc435-22a1-78f0-ab79-8131253fe7a4` retain the pass.
- Writer session `019fc439-9621-72d1-8d7a-381942901577`, trace
  `019fc439-968f-7032-a181-69e4bc802335`, run
  `e771f645-beac-4fb7-b67a-c6853ec0eeb9`, delegation
  `5f491f28-ee41-4e77-b317-9f807ea2ddfe`, finalization
  `6f753ee4-bc7a-4fd4-a4c5-33e1ba869f17`, and worker
  `codex-agent:019fc43a-3cee-7140-b5aa-aae25a3d679e` retain the `NO-GO`.

## exact-blocker

Actual Agency child workspace execution remains unproven. Store v2 localizes
the first failed boundary to three failed nested exec wrappers after correct
inference, launch, and trust. It intentionally retains no arguments, output, or
errors, so no more specific cause is claimed from this trial.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Reproduce the first nested-wrapper failure without another live writer and
   repair only that boundary; add a bounded failure category only if required.
2. Do not build or consume another sentinel until the focused wrapper proof is
   green. Never retry `c8a0577`, `4c57507`, `2bbd885`, or `b967ad2`.

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
  `d610630`, `7f0479f`, `be1ca0e`, `d5a4e31`, `c8a0577`, `4c57507`,
  `2bbd885`, and `b967ad2` consumed governed evidence; none may be rerun.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
