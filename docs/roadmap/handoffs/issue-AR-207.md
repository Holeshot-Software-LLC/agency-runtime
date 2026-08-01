---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-211-bound-immutable-commit-resolution.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/analysis/2026-07-31-ar-212-readme-story-evidence.html
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
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-214-context-delivery-authority
evidence_commit: 1694d6e07e04fb1c1f19f65bf2af381542b8079f
minimum_ledger_commit: 05bc8665f1c4024f9a3cdf16113020908e5141b0
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 210 merged the reviewed AR-212 repair as `1694d6e`; installation and
  autonomous activation pass, while its one product trial is consumed at
  context delivery.
- Exact official build `0.1.0+g1694d6e07e04` is installed.
- Bare install discovered only Codex and ZCode and selected the dashboard.
  ZCode completed, the dashboard is active and reachable, and Codex registered.
- AR-214 is locally repaired and demo-ready. The legacy accepted-staffing
  fixture reproduces `native_plan_scope_invalid` atomically; the repaired
  product prompt commits all five inference-authored units and exact Codex
  scopes. One reviewed exact-build activation and product trial remain.

## completed-evidence

- Default install dry-run selected exactly Codex, ZCode, and dashboard. The
  applied transaction created no other host integration.
- Dashboard scheduled-task registration is owned, current, active, reachable,
  and has no definition drift. No operator-presence ceremony was required.
- Autonomous activation session `019fbad0-9d80-70d0-8532-d1f49ff55df2`,
  trace `019fbad0-b2a3-7e93-b746-ac137b842b37`, and run
  `36d985a9-0e84-4e1e-9733-995bd1bb1d28` passed in 147.1 seconds.
- Activation inferred `code-reviewer`, persisted one route, plan row, grant,
  consumption, specialist load, native child, worker run, completed delegation,
  and accepted finalization. The first header was valid and corrections were
  zero. Trust was `autonomous_bypass`; persistent trust did not change.
- AR-214 root cause is the harness prompt's standalone prose `/`, parsed as an
  absolute resource while Markdown artifact paths and the proof dotfile were
  missed. The repair changes only prompt punctuation and resource normalization;
  explicit `/` remains invalid and never broadens to `.`.
- Failure schema v3 stores one allowlisted invariant. Direct SQLite inspection
  proves the row retains no prompt, path, or exception text; a true v41 fixture
  proves migration adds an empty invariant to existing rows.
- Focused AR-214 tests pass 3/3; canary/status projections pass 24/24; product
  contracts pass 33/33; dashboard UI passes 110/110. Repository-wide lint and
  formatting pass.
- The named production spine passes 641 tests with 6 skips. Every routing,
  policy, delegation, performance, scale, and CLI-startup gate passes.
  Decision conformance completes in 700.5 seconds, kills every curated mutation,
  and reports `source_unchanged=true`.
- Exact package installation reports `0.1.0+g1694d6e07e04`. The write-free bare
  plan selected exactly Codex, ZCode, and dashboard; application made ZCode
  current, left the Codex payload current, and made the per-user dashboard
  active and reachable.
- Autonomous activation session `019fbb30-eb27-7320-888c-9f86014be9ba`, trace
  `019fbb30-f3db-7193-b90f-31bef41efd1c`, and run
  `a3bb4d57-7b18-4827-afae-48fb6be298f8` passed in 123.2 seconds. Inference
  selected `code-reviewer`; one specialist load, native grant, consumption,
  worker run, and completed delegation were retained. Finalization accepted,
  the first header was valid, correction count was zero, trust mode was
  `autonomous_bypass`, and persistent trust did not change.
- Product trial `ar212-1694d6e-readme-01` is consumed and terminal `NO-GO` after
  96.2 seconds. Session `019fbb37-41ed-70e3-b211-5affbafb53c6`, trace
  `019fbb37-426b-7581-97e5-38f727e79327`, and run
  `6a4eaea4-e69c-4c4c-964c-0dedd23f390a` retain a repaired planner and applied
  recruiter, then `context_delivery_failed` with `validation_error`. Atomicity
  preserves zero routes, unit plans, specialist loads, grants, delegations,
  workers, finalizations, headers, or workspace writes. Correction count is
  zero because parent generation never began.
- A broader preflight module run reached 98 passes and exposed an unrelated
  stale-token/native-plan-scope failure. It is recorded as AR-213 / tracker
  https://github.com/Holeshot-Software-LLC/agency-runtime/issues/209 and is not
  part of this bounded repair.
- Builds and trials `cc322381`, `f0fde9ee`, `6b49f17d`, `5ad4aef`,
  `dd85e7d`, `584b949`, and `e62d0adc` remain consumed.

## exact-blocker

The local AR-214 repair is green but is not live proof. It must be reviewed,
merged, installed as one new exact build, and receive exactly one activation
and one governed product trial.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Do not convert
verifier output into a deterministic team or inferred gap. Do not rerun any
consumed activation or trial, mutate private trust state, label bypass as trust,
dispatch hosted Actions, or touch the owner's two untracked files.

## next-bounded-work-package

1. Commit, review, and merge the exact AR-214 head.
2. Install that build; run one activation and one product trial, then publish
   the local evidence page and OpenClaw handoff.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_ar214_context_delivery_authority.py -q -W error
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
- Exact builds `e62d0adc` and `1694d6e` have consumed activation and product trials.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
