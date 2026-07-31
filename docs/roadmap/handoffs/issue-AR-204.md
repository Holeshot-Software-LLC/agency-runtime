---
title: "AR-204 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-31
tags: [handoff, product, dashboard, inference, activation, automation]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-204
branch: codex/ar-203-activation-planning-contract
evidence_commit: 271e5a01d08b74dbe755662de997a32d04e5e735
minimum_ledger_commit: 3010813eaac39c0d799817cca19e0419acfbde59
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189
---

# AR-204 active recovery capsule

Bounded projection for making the README product story executable.

## checkpoint

- The product contract remains frozen: default full-suite install with opt-outs;
  mirrored owner CLI/dashboard controls; inference-only specialist staffing;
  one parent-only steward; explicit attended or supported bypass activation;
  first-pass evidence headers; and behavioral product proof.
- PR 191 merged the source story as `cc322381ec932452f0575445dc174510e4caad6f`
  and exact build `0.1.0+gcc322381ec93` is installed.
- Exact activation proves one real inferred specialist delegation with zero
  corrections. The only product trial for that build failed at workforce
  preflight and produced no artifact, so the README story remains `NO-GO`.
- Current source repairs that exact causal boundary and has accepted a real
  nine-specialist team for the README-shaped prompt.
- PR 192 merged and its exact build installed the README-default Codex, ZCode,
  and dashboard surfaces. Activation reached inference but rejected an
  over-decomposed canary before route commit; no product trial was consumed.

## completed-evidence

- Owner CLI/dashboard parity, authenticated reversible dashboard configuration,
  default dashboard inclusion, autonomous installation, terminal first-invalid
  headers, singleton stewardship, inference-only staffing, and product-host
  write/activation correlation are implemented and locally tested.
- Exact build activation recorded one grant, consumption, load, spawn, wait,
  completed delegation, worker run, accepted finalization, and zero corrections.
- Product trial `ar205-cc32238-readme-01` consumed that build's allowance and
  proved the hook reached `preflight_failed`; the workspace remained empty.
- The new planner/recruiter contract is still inference-owned. Deterministic
  code supplies acceptance constraints, typed recall, and reject-only safety
  checks; it does not plan, rank, select, or hire.
- Focused verification passes 84 tests. The isolated conformance evaluator
  passes its baseline and kills 44/44 curated mutations in 328.7 seconds with
  zero survivors or invalid results.
- The named fast Python spine passes 636 tests with 6 intentional skips;
  dashboard UI passes 110; routing evaluation 1.4.0 passes every gate;
  documentation validates 574 files; and Ruff checks all 602 Python inputs.
- The exact committed-tree decision-conformance rerun passed its baseline and
  killed 44/44 mutations in 327.7 seconds with zero survivors or invalid
  results and unchanged source.
- PR 192's first Codex review found three valid candidate defects. The bounded
  fixes enforce configured planner limits before recruitment, require positive
  release proof for each requested operation, and preserve explicitly requested
  communication capability. The second and final broad review found four more
  valid P1s in compact-budget clamping, operation-scoped proof, typed-recall
  size, and descriptive negation. All seven findings are repaired. The changed
  modules pass 83 tests; the wider routing/safety boundary passes 115 with one
  intentional skip.
- Commit `271e5a0` fixes the exact activation mismatch by carrying the canary's
  explicit one-unit `review-report` shape through inference. A fresh cloned-
  Store hook replay accepted inference-selected `code-reviewer`, one binding,
  and one immediate delegation assignment. Focused verification passes 72
  warning-strict tests; native installed proof remains.

## exact-blocker

The activation repair is committed and replay-proven but still needs its local
fast gate, merge, exact install, and native activation proof. README acceptance
then requires one fresh product trial to prove a real team, planned native
delegation, workspace artifacts, and zero corrections in the same run.

## same-task-continuity

Continue locally, stop at first failure, and do not dispatch hosted Actions
while GitHub spending is unavailable. Preserve the owner-untracked analysis and
lock files.

## next-bounded-work-package

1. Verify, merge, and exact-install the activation planning repair.
2. Prove native supported-bypass activation, then run the build's one product
   trial.
3. Generate the local evidence page and OpenClaw handoff only from recorded
   evidence.

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
python -c "from agency_runtime.cli.entrypoint import main; raise SystemExit(main())" eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Deterministic code may recall and verify but never select a specialist.
- Missing or invalid inference and malformed or corrected headers fail loudly.
- Dashboard and CLI parity covers supported owner configuration and controls.
- Supported Codex bypass never changes persistent trust or claims `trusted`.
- One live product trial per exact installed build; corrections must equal zero.
