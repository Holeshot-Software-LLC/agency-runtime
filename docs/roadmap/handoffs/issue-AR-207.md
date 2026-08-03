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
evidence_commit: 263e3f5
minimum_ledger_commit: 1c59ff34a0849e23d3935751c96eb97fbcb6ad11
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- Exact Store v3 repair/ledger checkpoint `e90af86`/`6e0d3c6` is locally green,
  builds canonically, and independently verifies. Wheel SHA-256 is
  `a5f69ae7d169e52ea051c45609922379d14e2ec8a86f9c0e3faa8b763bfa5c6d`;
  source SHA-256 is
  `e2bab035649401f3998b3472e7ffcd235aad4319ff0ae502b92e5d3c62f0a66c`.
- Autonomous install detects only Codex/ZCode, leaves the dashboard reachable,
  and passes activation with `code-reviewer`, accepted finalization, a valid
  first header, zero corrections, bypass, and no persistent trust change.
- Sole writer `ar223-agency-writer-6e0d3c6-01` is consumed `NO-GO`. Inference
  selects `minimal-change-engineer`; trust/header/correction gates pass, but the
  workspace is empty and finalization lacks `delegation_execution`.
- Exact Store v4 build `1c59ff3` canonically verifies; wheel SHA-256 is
  `275f0a1a46fe9e9bf457a55a7caee5ba29e426920163ad31ea976a29a901e563`.
- Autonomous install/activation passes for Codex/ZCode and dashboard with
  `code-reviewer`, valid first header, zero corrections, and bypass.
- Sole writer `ar223-agency-writer-1c59ff3-01` is consumed `NO-GO`; Store v4
  proves the nested patch wrapper failed before the absent-file shell check.
- Focused host A/B proves the cause: current Codex maps non-interactive
  `approval_policy=never` to managed read-only even when the CLI requests
  `workspace-write`. The documented `on-request` plus `auto_review` path
  creates and reads back the exact 21-byte sentinel without disabling the
  sandbox or changing persistent configuration.
- Exact implementation `263e3f5` passes 28 focused tests and one Agency-enabled
  no-build sentinel. Five inferred specialists launch and complete; both writer
  patch wrappers succeed, all read-only specialists have zero patch wrappers,
  and the exact workspace contains only the verified 29-byte sentinel.

## completed-evidence

- Activation session `019fc50b-837d-7171-b2c9-2f2a160d72c7`, trace
  `019fc50b-8fa5-7a83-8546-aed8cd5bd41f` retains the pass.
- Writer session `019fc50e-b34b-7932-b4ca-fa4ebbe61db8`, trace
  `019fc50e-b3d7-7633-bea9-c08e034f0ca9`, run
  `21aca342-8681-4e31-a78c-6b1d69f80321`, delegation
  `4336817f-dd28-49bf-a585-e2c3442d79cb`, and worker
  `codex-agent:019fc50f-5b8a-75c0-baf0-ee15992d9ce2` retain the `NO-GO`.
- Local repaired sentinel session `019fc528-cc4b-7a63-af76-bb7554c6832b` and
  trace `019fc528-ccd0-7b41-8fb1-adc90324be21` retain five completed children,
  exact patch and byte proof, a final five-specialist header, no correction
  prompt, autonomous bypass, and no persistent trust mutation.

## exact-blocker

Actual Agency child workspace execution is now proven locally with Agency
enabled. Immutable installed-build proof remains pending; the consumed v4 trial
is not retried.

## same-task-continuity

Keep inference authoritative and the parent non-working. Deterministic code may
carry verified scope and validate host evidence but may not select specialists.
Do not treat a terminal child turn as task-execution proof, rerun consumed
evidence, broaden into AR-213 or AR-222, mutate persistent trust, dispatch
hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. From the clean checkpoint, produce one canonical immutable build, install it
   autonomously for Codex/ZCode/dashboard, and consume one activation.
2. Only after activation passes, consume one fresh governed writer sentinel.
   Stop at its first terminal boundary; never retry `5a97976`, `6e0d3c6`, or
   `1c59ff3`.

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
