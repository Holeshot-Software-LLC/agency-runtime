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
evidence_commit: e0912521d036646e0a439dd2cdfb8380828ff480
minimum_ledger_commit: 5a97976ba6e1c37333577448f835bb15c3eceedf
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The goal remains `README's main story works in reality.` Exact repair/ledger
  checkpoint `e091252`/`5a97976` rebases product execution temp variables into
  the exact trusted workspace without disabling sandboxing.
- Focused product-host/Store checks pass 43 tests. The named spine passes 657
  with six skips; 110 dashboard tests, Ruff/docs, and routing thresholds pass.
  The unchanged-source decision-conformance CLI returned no verdict before its
  304- and 904-second deadlines and was not retried again.
- Exact `5a97976ba6e1c37333577448f835bb15c3eceedf` builds canonically and
  independently verifies. Wheel SHA-256 is `a7542966b2a1f243f3c91c2573c0880ca01a37a88a0efb5e0037734f33d2ef7d`;
  source SHA-256 is `10f25d3e3c096966fae31fd1c5e1b2decce6e9e4eaa37d5ecda8d31c4f167962`.
- Its full-suite autonomous install refreshes Codex and ZCode, leaves the
  dashboard active/reachable, and passes activation with inferred/executed
  `code-reviewer`, accepted finalization, valid first header, zero corrections,
  trust bypass, and no persistent profile change.
- Sole writer `ar223-agency-writer-5a97976-01` is consumed `NO-GO`. Inference
  selects/loads `minimal-change-engineer`; exact-workspace trust, hook bypass,
  valid first header, and zero corrections pass. The workspace remains empty
  and finalization declines missing `delegation_execution`.
- Store v2 records one classified nested `apply_patch`, one fixed failed wrapper,
  zero unclassified inputs, and zero missing outputs. The temp rebase was
  insufficient and does not prove the wrapper cause.

## completed-evidence

- Activation session `019fc484-4337-77d0-909b-d6976897feb4`, trace
  `019fc484-4b88-75a1-9eb8-b9785d4f0f6d`, and worker
  `codex-agent:019fc484-f8bc-7690-88e5-c34425513249` retain the pass.
- Writer session `019fc487-b580-7083-ab02-6278567f7ff7`, trace
  `019fc487-b5f5-7c13-959b-897fb1f9ff6e`, run
  `23a10be7-1469-4009-8d0f-9180c2e05e6f`, delegation
  `366c7249-4cf0-43a2-8190-fdc9d00caf91`, and worker
  `codex-agent:019fc488-5f7f-7b81-8686-d55471e433dc` retain the `NO-GO`.

## exact-blocker

Actual Agency child workspace execution remains unproven. The temp-root repair
did not clear the nested wrapper failure. Store v2 proves where it failed but
does not distinguish a small fixed cause; the consumed trial is not retried.
Store v3 classification is locally green but has not yet been built or used by
a new immutable writer.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Produce one exact canonical build from the Store v3 checkpoint, install the
   full suite autonomously, and require activation to pass first.
2. Run one new writer sentinel only. Use its v3 receipt to fix the named cause
   or admit the workspace write. Never retry `c8a0577`, `4c57507`, `2bbd885`,
   `b967ad2`, or `5a97976`.

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
