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
evidence_commit: f349c21c5ce6259b7337ec9d44c52e7b3aef156f
minimum_ledger_commit: 2338c8fb995c550a0ce5ad534f52253185b37a82
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
- PR 193 merged exact revision `f0fde9ee929e13587f62dd85147cf63b18b5d37e`;
  exact build `0.1.0+gf0fde9ee929e` installed the README-default Codex, ZCode,
  and dashboard surfaces.
- Its supported-bypass activation is correction-free and proves inferred
  `code-reviewer`, specialist load, native spawn/wait, completed delegation,
  worker run, and finalization on one exact trace.
- Its sole product trial, `ar205-f0fde9e-readme-01`, is terminal `NO-GO` after
  101.1 seconds: the hook reached `preflight_failed`, no route or response was
  published, and the workspace remained empty. Do not rerun that build.
- An exact-prompt private Store replay proves planning and recruiting applied,
  10 of 11 units were staffed, and one documentation gap was declared, but the
  product's restricted canary environment suppressed gap hiring entirely.

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
- PR 193 merged that repair; exact installation and native activation now pass.
  The product replay also proves Codex advertised repository-write,
  test-execution, and native-delegation capabilities, excluding host eligibility
  as the current blocker.
- Commit `f349c21` repairs product gap-hiring eligibility and removes repeated
  full-request copies from the isolated delegation plan. The focused boundary
  passes 169 tests with one skip. Two accepted product-shaped routes then hit
  the same 8,192-character parent-context ceiling at nine and ten units.
- Sizing proves the compact form needs 8,326 characters for ten realistic units
  and 9,534 for the configured maximum sixteen; the general preflight and Codex
  hook ceilings are 32,000 and 48,000 respectively.
- AR-206 proves this task's evidence Store is healthy. Its 558-node routing
  decision exactly matches the ready receipt, but the immutable old Stop hook
  rejects it under a stale 256-node verifier cap. The source now uses the
  durable 2,048-node bound and passes its focused regression and mutation tests.

## exact-blocker

The exact installed build passes activation and the source candidate reaches
accepted inferred product teams. README acceptance is waiting for owner
direction after the same context ceiling failed twice. Raising persistent hosts
to the existing 32,000-character preflight ceiling is recommended; forcing a
smaller team would undercut the complete specialist-plan contract.

## same-task-continuity

Continue locally, stop at first failure, and do not dispatch hosted Actions
while GitHub spending is unavailable. Preserve the owner-untracked analysis and
lock files.

## next-bounded-work-package

1. Resolve the context-ceiling choice; recommended: 32,000 characters with the
   unchanged 48,000-character Codex hook boundary.
2. Implement and verify only that policy, include the bounded AR-206 verifier
   repair, then merge, exact-install, re-prove activation, and run one product
   trial for only that new exact build.
3. Generate the local evidence page and OpenClaw handoff only after the product
   gate proves real execution and zero corrections.

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
