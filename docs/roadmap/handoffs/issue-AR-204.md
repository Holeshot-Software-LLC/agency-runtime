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
  - docs/roadmap/issue-AR-206-accept-bounded-ready-routing-receipts.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0123-use-general-preflight-ceiling-for-persistent-parents.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-204
branch: codex/ar-204-readme-product-proof
evidence_commit: 7727c0cd9bba3824acd3722c6c3964086667cfc9
minimum_ledger_commit: 4081265af803f85ecafb5372a74e0fd06a93e110
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
- PR 195 merged exact revision `6b49f17d6787823f9ba78a8f09383001b6a77535`;
  exact build `0.1.0+g6b49f17d6787` is installed for Codex, ZCode, and dashboard.
- Supported-bypass activation is correction-free and proves AR-206 plus one
  complete inference-selected `code-reviewer` lifecycle.
- Product trial `ar205-6b49f17-readme-01` is terminal `NO-GO` after 100.174
  seconds. Its accepted route contains eight units and nine specialists, but
  it recorded no grant, load, worker run, or native spawn/wait. The workspace
  remained empty and no response/header was published. Do not rerun this build.
- AR-207 tracker issue #196 owns the content-free preflight/delegation failure
  evidence and the next executable repair.

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
- ADR-0123 is approved and commit 839ddee uses the 32,000-character persistent
  parent ceiling. A complete sixteen-unit regression crosses 8,192, its
  legacy-cap mutation is killed, and the 115-test focused boundary passes.
- The exact post-review committed tree passes the named fast Python spine (636
  passed, 6 skipped), dashboard UI (110 passed), every routing evaluation gate,
  Ruff across 602 files, all 52 decision mutations with zero survivors or
  invalid results and unchanged source, and documentation validation for 578
  files.
- PR 195 review found and prompted two bounded repairs: exact encoded context
  output is checked before ready commit, and stored version-11 recipes retain
  their full-goal renderer. Four direct tests, 113 affected tests with one skip,
  six exact replay nodes with one skip, and both new mutations pass.
- PR 195's exact reviewed head passed 238 affected tests, the 636-test named
  spine with 6 skips, all 110 dashboard tests, every routing gate, all 53
  mutations, Ruff, 579 documentation files, and diff integrity before merge.
- A disabled-Agency Sol control returned exact `PROBE_OK`. A separate enabled
  diagnostic ended `preflight_failed` after 91.146 seconds and retained only a
  run row: no route, model receipt, or bounded failure reason. The source catch
  path discards that evidence today.

## exact-blocker

Exact installation, activation, AR-206, and inference-selected product staffing
pass. README acceptance is blocked after staffing: the parent did not execute
native delegation, and adjacent preflight failures are not diagnosable without
replay.

## same-task-continuity

Continue locally, stop at first failure, and do not dispatch hosted Actions
while GitHub spending is unavailable. Preserve the owner-untracked analysis and
lock files.

## next-bounded-work-package

1. Persist and project bounded content-free preflight/delegation failure facts.
2. Use bounded controls to repair the first demonstrated no-spawn cause; run
   focused tests and decision mutations.
3. Complete at most two review passes, run the named fast spine, merge, and
   exact-install before one fresh product trial.
4. Generate the local evidence page and OpenClaw handoff after that terminal
   exact-build trial.

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
