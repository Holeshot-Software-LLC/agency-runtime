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
evidence_commit: dbd5502847b822825c7f3b99a18662949c98de0b
minimum_ledger_commit: e9c006570eafa7db8814d87fe2655c1d2cea9a35
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
---

# AR-203 active recovery capsule

## checkpoint

- AR-201 terminal trial `ar201-ed4450e-ordinary-01` remains preserved as
  `NO-GO`; it will not be rerun or reinterpreted.
- PR 184 merged the combined repair normally as
  `dbd5502847b822825c7f3b99a18662949c98de0b`.
- Exact build `0.1.0+gdbd5502847b8` is installed; only Codex and ZCode were
  refreshed.
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
- GitHub hosted jobs were refused before repository execution by account
  billing enforcement.
- Trial `ar203-dbd5502-ordinary-01` is terminal `NO-GO`: isolated trust was
  proven, but workspace-write, Agency activation, and the final header were not.
- Correction count was zero. Every runtime cardinality was zero, and product
  grading correctly skipped before inspecting the empty workspace.
- Canonical product prompt hash is
  `sha256:e845c233e9a65eff66a8af626a333110449e6c90f8f4b46b0f6529ddd427152d`;
  executed wrapper hash is
  `sha256:3218b84c7cc13a7a8648ef9c65f6756d5dcba45b0d3ccc1553e302de27d5ddae`.
- Codex completed with host exit zero in 87.813 seconds and a 308-character
  response. The product command exited one after `route_not_found`,
  `proof_file_missing`, and the absent header.
- Exact workspace trust was `proven: true`, scoped to the disposable
  workspace, and left persistent configuration unchanged. Effective
  workspace-write was `proven: false`.

## exact-blocker

The exact activation and write-proof implementation, merge, and installation
are complete. The final trial proved the isolated trust projection but not
effective workspace-write, and it recorded no matching Agency route or header.

## same-task-continuity

Keep fail-closed grading and the bounded proof repair frozen. Do not add a
general sandbox bypass, mutate persistent trust, add another write directory,
or reinterpret `correction_count: 0` as a pass when the header is absent.

## next-bounded-work-package

1. Reproduce the restricted-token ability to create and write the exact trial
   directory before launching Codex.
2. Add bounded hook-start evidence that distinguishes hook non-execution from a
   Store query miss.
3. Request explicit authorization before a replacement ordinary canary.

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
