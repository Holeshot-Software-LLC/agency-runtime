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
  - docs/decisions/0123-use-general-preflight-ceiling-for-persistent-parents.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-203
branch: codex/ar-204-readme-product-proof
evidence_commit: 839ddee4551ab99c8997e281caf9e1633788d9f8
minimum_ledger_commit: 856191bac8f0b638dbbfcb303f01db404d84240f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
---

# AR-203 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 193 merged exact revision `f0fde9ee929e13587f62dd85147cf63b18b5d37e`;
  build `0.1.0+gf0fde9ee929e` is installed for Codex, ZCode, and dashboard.
- Supported-bypass activation passed on that exact build with zero corrections.
  Session `019fb729-5164-70f3-8b9e-e55902eb33c7`, trace
  `019fb729-5d2e-73a3-8a3b-03a4a02f57b7`, and route
  `c8950037-541e-4eb8-984a-a68f4db156f2` prove inferred `code-reviewer`, one
  grant and consumption, specialist load, native spawn/wait, completed
  delegation, worker run, and accepted finalization.
- Product trial `ar205-f0fde9e-readme-01` is terminal `NO-GO`: 101.1 seconds,
  host exit zero, CLI exit one, zero corrections, no response/header/route,
  no workspace-write proof, and an empty workspace. Its allowance is consumed.
- Production Store run `3833f8ae-34c2-4ebc-8f1c-9b481bd720e0`, session
  `019fb72b-d385-72c1-92c5-baf6cec8cf5a`, trace
  `019fb72b-d3f3-76c2-ba3f-1b7d5eb2519b` proves the hook reached
  `preflight_failed`; this was not a trust, registration, or Codex-startup
  failure.
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
- Exact prompt reconstruction verified product hash
  `788dee12f4652c37f81b3b97191c1770d515ee054abf9001f6f613db48d03144`
  and executed hash
  `1b745998a521010b9ceb8deeb6351d1ca9dd98bf6c4d4da80239f88aeff14e7b`.
  A private cloned-Store replay reproduced the failure: planner and recruiter
  responses were applied; inference authored 11 units and staffed 10; the
  documentation unit was an explicit `inference-declared-gap`; repository
  write and test capabilities were proven; and no hiring event ran.
- Commit `f349c21` removes the environment-wide hiring suppression, preserves
  the exact activation task's separate no-hiring branch, encodes the repeated
  request prefix once across native unit goals, and advances the durable
  context recipe to v12. Its focused boundary passes 169 tests with one
  intentional skip; Ruff and whitespace checks pass.
- A post-repair replay accepted nine planned units and ten specialists before
  exposing the 8,192-character isolated-parent ceiling. After prefix encoding
  and v12 alignment, a second replay accepted ten units and nine specialists
  with no staffing reasons, then reached the same ceiling. Per the bounded
  delivery contract, work stops at this repeated causal boundary for owner
  direction.
- Read-only sizing measures 8,120 characters for nine realistic units, 8,326
  for ten, and 9,534 for the configured maximum sixteen. The general preflight
  ceiling is 32,000 and the Codex hook ceiling is 48,000.
- The owner approved ADR-0123. Commit 839ddee applies the 32,000-character
  persistent-host ceiling, proves a complete sixteen-unit context crosses the
  legacy limit, and kills the mutation restoring 8,192. The focused boundary
  passes 115 tests; ledger commit 856191b records the checkpoint.
- The exact committed tree passes the named fast Python spine (636 passed,
  6 skipped), dashboard UI (110 passed), every routing evaluation gate, Ruff
  across 602 files, and all 50 decision mutations with source unchanged.
  Documentation validation passes for 577 files and the tree is whitespace
  clean.
- PR 195 review found two valid boundaries. The source candidate now rejects a
  multibyte context above the 48,000-byte exact envelope reserve before ready,
  keeps the 65,536-byte hook output hard cap, and renders version-11 recipes
  with full goals instead of version-12+ prefix compaction. Four direct tests,
  113 affected tests with one skip, six exact replay nodes with one skip, and
  both new mutations pass.

## exact-blocker

Installation and activation pass, gap hiring is separated correctly, inference
reaches accepted product teams, and the approved context policy is fast-green.
The remaining blocker is rerunning the invalidated fast gates, pushing the PR
195 review repairs, merge, and exact installation before one new-build trial.

## same-task-continuity

Keep inference authoritative. Do not add deterministic selection, weaken
fail-closed validation, mutate private trust state, or rerun a product trial on
`cc322381` or `f0fde9ee`.

## next-bounded-work-package

1. Run the named fast gate and all 52 decision mutations, then push and obtain
   one focused re-review of the repaired PR head.
2. Merge, exact-install, and re-prove activation with the AR-206 verifier fix.
3. Spend one product trial only on that new exact build. Require a real inferred
   team or hired contractor, planned delegation, workspace artifacts, and zero
   corrections before producing the evidence page and OpenClaw handoff.

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
