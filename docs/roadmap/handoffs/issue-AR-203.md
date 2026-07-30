---
title: "AR-203 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [handoff, evaluation, codex, activation, workspace, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-203
branch: agent/ar-203-readme-story-proof
evidence_commit: baaf603fc65f4ea338bcdde19f60c60a4c6f96af
minimum_ledger_commit: e5a11f2e77ba4589ae93e610f303946b0efdde48
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
---

# AR-203 active recovery capsule

## checkpoint

- PR 186 merged the reviewed launch repair as exact main revision
  `830b878859318bc1288858ba65ba580bd98bf53e`.
- Exact build `0.1.0+g830b87885931` is installed for Codex and ZCode only; the
  dashboard remained opted out. The owner trusted the refreshed Codex hooks and
  restarted before the trial.
- Trial `ar203-830b878-ordinary-02` is terminal `NO-GO`. It proves activation
  and nine-unit planning, then fails at recruiter response acceptance/recovery.
- No source repair has started. This checkpoint freezes the first causal
  boundary before implementation.
- The README-story goal is bounded to one ordinary Codex proof on this machine:
  first terminal failure or 45 minutes ends a package, one live trial is
  allowed per exact build, and a second failure at the same causal boundary
  stops for owner direction.
- Owner-untracked analysis and lock files remain untouched.

## completed-evidence

- Codex exited zero after 182.422 seconds; the product wrapper exited one after
  183.335 seconds with empty stderr. The trial workspace remained empty.
- Exact trace `019fb417-f166-7461-a1db-e53ee0007045` contains one route, one
  run, three correlated model receipts, two finalizations, and nine typed work
  units sourced from `verified-workforce-plan`.
- Inference attempt one applied the planner response. Attempt two rejected the
  recruiter response as `provider_response_contract_invalid`. Attempt three,
  the bounded repair, failed as `provider_no_valid_response`.
- The route ended `abstained`, the run ended `retry_exhausted`, and staffing
  recorded `workforce_inference_failed`. Of 272 candidates, 53 were eligible
  and 219 were rejected before inference-owned selection.
- No specialist was selected. Hiring recorded `no_attempt`; loads,
  delegations, worker runs, native spawns, and native waits were all zero.
- The final response contained all seven header fields but required one Stop
  correction. `correction_count: 1` independently fails the canary.
- Isolated workspace trust was proven and the persistent profile was unchanged.
  The proof file was missing, so effective workspace-write was not proven and
  product validation correctly skipped.
- Product prompt hash is
  `sha256:092f36f658e877437f1434326bd39a57a8995bcf64860cdc60560e6ea915f852`;
  executed wrapper hash is
  `sha256:4e6ee868cf1d528016e3625d9bd8069bd2f71c8d7ebef020b26efb5a88b964f7`.
- Workspace hash is
  `sha256:e49c785ca29e47c943071c9b38914c19c0ac7095cad9d65569d25c9bb8542fe3`;
  session ID is `019fb417-f0e7-7702-ac1b-5bf74e07c1dd`.
- The merged source repair remains green: changed-component suite 200 passed;
  named fast Python spine 675 passed and 6 skipped; dashboard UI 109 passed;
  routing evaluation 1.3.0 passed every gate; decision conformance killed 19/19
  mutations; documentation and Ruff checks passed.

## exact-blocker

Activation and planning now work in the exact installed build. The first causal
boundary is recruiter response contract acceptance: the configured inference
provider produced a planner response the runtime accepted, then a recruiter
response the runtime rejected, and one bounded repair could not produce a valid
replacement. This is not a hook-start, trust, deterministic-selection, hiring,
delegation, or workspace-grading failure.

## same-task-continuity

Keep inference authoritative for online selection. Do not add deterministic
role anchors, weaken fail-closed schemas, add a general sandbox bypass, mutate
persistent trust, or reinterpret one corrected header as a first-pass success.

## next-bounded-work-package

1. Publish this terminal trial in the local evidence page and checkpoint the
   canonical roadmap state.
2. Reproduce and repair only recruiter response acceptance or its one bounded
   semantic repair; preserve inference-owned staffing and fail-closed evidence.
3. Run focused tests, at most two review passes, decision conformance, and the
   named fast verification spine. Stop at the first new terminal failure.
4. PR and merge the reviewed slice, exact-install it for Codex and ZCode only,
   then run one replacement trial for that new build.
5. A second failure at this same recruiter boundary stops for owner direction;
   otherwise publish the final local report and continue from the next proven
   boundary.

## verification

~~~text
python -m pytest tests/test_canary_cohesion.py tests/test_host_canary.py tests/test_product_host.py tests/test_product_one_shot.py tests/test_workforce_inference.py -q -W error
agency eval decision-conformance --repository . --json
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Persistent Codex trust configuration remains outside the mutation boundary.
- The product host retains sandboxing and receives no extra write root.
- The sentinel proves one exact in-workspace write, not exhaustive host
  sandbox correctness.
- Touch only Codex and ZCode on this machine.
- Correction count greater than zero or absent is a final canary failure.
- Do not launch more than one live trial for one exact installed build.
- End a bounded package at its first terminal failure or 45 minutes.
