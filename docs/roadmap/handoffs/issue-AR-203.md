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
branch: agent/ar-203-hook-start-workspace
evidence_commit: baaf603fc65f4ea338bcdde19f60c60a4c6f96af
minimum_ledger_commit: e5a11f2e77ba4589ae93e610f303946b0efdde48
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
- A replacement live canary was not launched: the approval boundary requires
  fresh explicit owner authorization after the prior authorized final trial.
- Current context telemetry reports 85.7 percent remaining. This bounded launch
  repair is being checkpointed before mutation evaluation and the fast spine.

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
- Exact Store queries for both the canonical and wrapped product prompt hashes
  returned no route, and the latest persisted route predates the final trial.
  The missing activation is therefore a hook-start failure, not merely a
  product-report hash mismatch.
- The product launch contract now persists the parent turn, enables
  `multi_agent_v2` and `agents.enabled=true`, and retains bounded
  `workspace-write` with no added write root or full-access bypass.
- Isolated product hooks now require the pre-existing Store. Optional
  product-canary diagnostics project only canonical hook event names with
  bounded accepted/completed/failed counts; raw stderr is never retained.
- Product trials remain multi-unit and do not reuse the activation canary's
  single-spawn rollout constraint. Codex specialist instructions require
  `fork_turns=none` plus the row's exact native task name.
- The repaired slice passes 26 focused tests, including red-to-green product
  launch, environment, hook emission, hook projection, proof projection, and
  two-unit delegation contracts. Mutation evaluation remains pending.

## exact-blocker

The prior exact activation and write-proof implementation is merged and
installed, but the final trial recorded no matching Agency route or header.
The newly identified stale product launch contract is repaired locally and
awaits mutation evaluation, fast verification, review, merge, and exact
installation before a replacement live canary.

## same-task-continuity

Keep fail-closed grading and the bounded proof repair frozen. Do not add a
general sandbox bypass, mutate persistent trust, add another write directory,
or reinterpret `correction_count: 0` as a pass when the header is absent.

## next-bounded-work-package

1. Kill every curated decision mutation and complete two bounded review passes.
2. Run the named fast production spine and reach demo-ready.
3. Merge and install the exact build for Codex and ZCode only.
4. Request explicit authorization for one replacement ordinary canary, then use
   its hook-stage evidence to distinguish non-invocation from handler failure.

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
