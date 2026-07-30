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
branch: agent/ar-202-recruiter-repair-convergence
evidence_commit: 9f3d72a738dd9c374116cd2a64d6a18a572681ea
minimum_ledger_commit: fdf4a36d8b5e117b75c8bc713b9e6464b1f78438
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
---

# AR-203 active recovery capsule

## checkpoint

- AR-201 terminal trial `ar201-ed4450e-ordinary-01` remains preserved as
  `NO-GO`; it will not be rerun or reinterpreted.
- The combined AR-202/AR-203 source repair is in focused review on
  `agent/ar-202-recruiter-repair-convergence`.
- Owner-untracked analysis and lock files remain untouched.
- Context telemetry reported 47.8 percent remaining, so this reviewed source
  slice requires a clean substantive and ledger checkpoint before the fast
  production spine.

## completed-evidence

- Product Agency mode consumes
  `agency.canary-activation-evidence.v1` from the exact executed prompt hash.
  A regression raises if the legacy recent-activity summary is requested.
- A disposable Codex home receives one exact canonical workspace trust entry.
  The persistent source configuration remains byte-identical.
- The host command retains `--sandbox workspace-write`, supplies no
  `--add-dir`, and does not request `danger-full-access`.
- The same Codex invocation must create a fixed prompt-bound sentinel. The
  harness accepts only its exact bounded regular-file value, removes it before
  grading, and rejects preexisting, missing, mismatched, linked, oversized, or
  uncleanable proof.
- Missing or null workspace-write evidence skips product validation and cannot
  pass the trial.
- Focused runtime review passes 85 tests. Decision conformance passes its
  baseline and kills 13/13 mutations with zero survivors or invalid results;
  source inputs remain unchanged.
- The exact checkpoint is substantive commit `9f3d72a` plus ledger
  `fdf4a36`.
- Named fast Python spine: 675 passed, 6 skipped. Dashboard UI: 109 passed
  after the outer sandbox's expected `spawn EPERM` required the authorized
  rerun. Routing evaluation 1.3.0 passed every gate; routing p95 was 3.725 ms
  and cache-hit p95 was 0.989 ms.

## exact-blocker

The source boundary and named fast gate are complete, but the merged revision,
exact Codex/ZCode installation, and one final ordinary canary do not yet exist.

## same-task-continuity

Do not launch another AR-201 trial. Finish the bounded combined repair, merge
and exact-install it, then spend one final ordinary Codex product canary.

## next-bounded-work-package

1. Push, open the PR, resolve required checks, and merge.
2. Install the exact merged revision for Codex and ZCode only.
3. Run one final ordinary product canary and publish the local evidence report.

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
