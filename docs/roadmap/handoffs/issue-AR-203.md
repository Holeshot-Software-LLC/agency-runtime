---
title: "AR-203 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-31
tags: [handoff, evaluation, codex, activation, workspace, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-203
branch: codex/ar-203-activation-planning-contract
evidence_commit: 271e5a01d08b74dbe755662de997a32d04e5e735
minimum_ledger_commit: 3010813eaac39c0d799817cca19e0419acfbde59
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
---

# AR-203 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 192 merged exact revision `9461099479f851b9440d825f889aa079950a298c`;
  build `0.1.0+g9461099479f8` is installed for Codex, ZCode, and dashboard.
- Activation trace `019fb676-df24-72c1-bf3e-af3a23222ff8` proves real
  inference-selected `code-reviewer` injection and a complete native child
  lifecycle with zero corrections.
- Product trial `ar205-cc32238-readme-01` is terminal `NO-GO`: 49.327 seconds,
  CLI exit one, no workspace files, and a matching `preflight_failed` session.
  Its one-trial allowance is consumed.
- Supported-bypass activation reached inference with zero response corrections
  but failed before route commit: the exact canary was split into two bindings.
- Commit `271e5a0` carries the explicit one-unit `review-report` contract through
  inference; its fresh cloned-Store hook replay accepted `code-reviewer` with
  one binding and assignment. Native installed proof is not yet claimed.
- The two owner-untracked files remain untouched.

## completed-evidence

- The exact failed product session proves UserPromptSubmit ran, classified the
  prompt substantive, and failed during workforce planning before route commit.
- A bounded direct replay reproduced contradictory planner/validator assurance
  rules and missing recruiter coverage evidence without creating product files
  or committing a contractor.
- The repaired planner receives a deterministic acceptance contract and exact
  structured veto guidance, then authors its own complete replacement plan.
- The repaired recruiter receives deterministic, non-ranked typed coverage and
  uncovered requirements, then owns candidate ranking, staffing, and gap
  declaration.
- A fresh replay accepted nine units and nine specialist assignments with no
  staffing reasons. Focused tests pass 84 cases; decision conformance kills
  44/44 mutations with zero survivors or invalid results.
- The named fast Python spine passes 636 tests with 6 intentional skips;
  dashboard UI passes 110; routing evaluation 1.4.0 passes every gate;
  documentation validates 574 files; and Ruff checks all 602 Python inputs.
- The exact committed-tree decision-conformance rerun passed its baseline and
  killed 44/44 mutations in 327.7 seconds with zero survivors or invalid
  results and unchanged source.
- PR 192 merged after two broad review passes. Its first review found three valid
  contract leaks; configured planner limits, operation-specific positive
  release proof, and explicitly requested communication coverage are now
  repaired. Its second and final broad review found four more valid P1s:
  compact-budget clamping, operation-scoped release proof, bounded typed
  recall, and descriptive-negation preservation. All seven findings are now
  repaired. The changed modules pass 83 warning-strict tests, and the wider
  routing/safety boundary passes 115 tests with one intentional skip.
- Exact activation diagnostics isolated `binding_count` and then
  `artifact_kind`; both provider stages were applied, proving this was a
  planner-contract mismatch rather than unavailable inference or trust refusal.
- The repair rejects and repairs over-broad planner output through inference,
  preserves ordinary open-ended planning, and adds two decision mutations.
  Its focused boundary passes 72 warning-strict tests; a fresh real-provider
  cloned-Store replay accepted one inferred review unit and `code-reviewer`.

## exact-blocker

The activation planning repair is committed and replay-proven but not yet
merged or installed. After its local fast gate, it needs a small PR, exact
install, and native activation proof. Only then may one fresh exact-build
product trial attempt route, delegation, workspace write, artifacts, and zero
corrections together.

## same-task-continuity

Keep inference authoritative. Do not add deterministic selection, weaken
fail-closed validation, mutate private trust state, or rerun a product trial on
`cc322381`.

## next-bounded-work-package

1. Run the local fast gate, merge the activation repair, and exact-install it.
2. Prove native supported-bypass activation on that exact installed build.
3. Run its one supported-bypassed product trial. If it passes, produce the
   local evidence page and OpenClaw handoff; if it
   fails, stop at the first newly proven causal boundary.

## verification

~~~text
python -m pytest tests/test_workforce_intent.py tests/test_workforce_inference.py tests/test_decision_conformance.py -q -W error
python -c "from agency_runtime.cli.entrypoint import main; raise SystemExit(main())" eval decision-conformance --repository . --json
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
~~~

## constraints

- Product host remains sandboxed and receives no extra write root.
- Touch only Codex, ZCode, and dashboard on this machine.
- Supported bypass evidence is `bypassed`, never `trusted`.
- One live product trial per exact installed build; any correction is failure.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
