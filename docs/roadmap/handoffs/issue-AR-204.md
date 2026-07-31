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
branch: codex/ar-203-product-planner-repair
evidence_commit: 38e7e1c700a3ff429071ef42556040cfdc22469d
minimum_ledger_commit: 2c70710b1d435cc95a5d256aea1d100322c9ae77
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
  documentation validates 571 files; and Ruff checks all 602 Python inputs.
- The exact committed-tree decision-conformance rerun passed its baseline and
  killed 44/44 mutations in 327.3 seconds with zero survivors or invalid
  results and unchanged source.

## exact-blocker

The current source needs a commit/ledger checkpoint, reviewed merge, exact
install, and one fresh product trial. README acceptance
still requires the same run to prove a real team, planned native delegation,
workspace artifacts, and zero response corrections.

## same-task-continuity

Continue locally, stop at first failure, and do not dispatch hosted Actions
while GitHub spending is unavailable. Preserve the owner-untracked analysis and
lock files.

## next-bounded-work-package

1. Commit the locally verified source plus exact ledger.
2. Push, review, merge, and exact-install the new build.
3. Run one supported trust-bypassed native Codex product trial.
4. Generate the local evidence page and OpenClaw handoff only from recorded
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
