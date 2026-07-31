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
branch: codex/ar-203-product-planner-repair
evidence_commit: 38e7e1c700a3ff429071ef42556040cfdc22469d
minimum_ledger_commit: 2c70710b1d435cc95a5d256aea1d100322c9ae77
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
---

# AR-203 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 191 merged exact revision `cc322381ec932452f0575445dc174510e4caad6f`;
  build `0.1.0+gcc322381ec93` is installed for the scoped local suite.
- Activation trace `019fb676-df24-72c1-bf3e-af3a23222ff8` proves real
  inference-selected `code-reviewer` injection and a complete native child
  lifecycle with zero corrections.
- Product trial `ar205-cc32238-readme-01` is terminal `NO-GO`: 49.327 seconds,
  CLI exit one, no workspace files, and a matching `preflight_failed` session.
  Its one-trial allowance is consumed.
- The current branch fixes the first causal preflight boundary. A live provider
  replay now accepts a complete inferred specialist team; end-to-end product
  execution is deliberately not claimed.
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
  documentation validates 571 files; and Ruff checks all 602 Python inputs.
- The exact committed-tree decision-conformance rerun passed its baseline and
  killed 44/44 mutations in 327.3 seconds with zero survivors or invalid
  results and unchanged source.
- PR 192 is open and mergeable. Its first Codex review found three valid
  contract leaks; configured planner limits, operation-specific positive
  release proof, and explicitly requested communication coverage are now
  repaired. The changed modules pass 79 warning-strict tests, and the wider
  routing/safety boundary passes 115 tests with one intentional skip.

## exact-blocker

The causal source boundary and first-review findings are repaired locally, but
the updated PR still needs its second review pass, merge, and exact install. One
fresh exact-build product trial must then prove route, delegation, workspace
write, artifacts, and correction count zero together. The older report's
`route_not_found` projection also understates its matching `preflight_failed`
session and remains a traceability follow-up unless it blocks the final report.

## same-task-continuity

Keep inference authoritative. Do not add deterministic selection, weaken
fail-closed validation, mutate private trust state, or rerun a product trial on
`cc322381`.

## next-bounded-work-package

1. Commit and push the first-review repair plus its immediate ledger.
2. Complete the second review pass, merge, and exact-install the new build for
   Codex, ZCode, and dashboard.
3. Run one supported bypassed product trial for that exact merge.
4. If it passes, produce the local evidence page and OpenClaw handoff; if it
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
