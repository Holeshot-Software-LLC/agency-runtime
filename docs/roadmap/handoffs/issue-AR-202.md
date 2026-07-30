---
title: "AR-202 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [handoff, workforce, recruiter, repair, evidence, recovery]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/decisions/0115-aggregate-bounded-recruiter-repair-failures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-202
branch: agent/ar-202-recruiter-repair-convergence
evidence_commit: dbd5502847b822825c7f3b99a18662949c98de0b
minimum_ledger_commit: e9c006570eafa7db8814d87fe2655c1d2cea9a35
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/182
---

# AR-202 active recovery capsule

## checkpoint

- AR-201 merged as exact main revision
  `ed4450e9cb55c656d70c94026b22f6caebbd45e1` and is installed as build
  `0.1.0+ged4450e9cb55`.
- The operator deliberately set `workforce.fast_call_budget` to three before
  Codex and ZCode refresh. Codex bundle `0.1.0+codex.2743f1b2ec20` serializes
  185-second timeouts; ZCode serializes 185000-millisecond timeouts.
- Trial `ar201-ed4450e-ordinary-01` is terminal `NO-GO` and will not be rerun or
  reinterpreted.
- Work continues from exact merged main on
  `agent/ar-202-recruiter-repair-convergence`.
- Owner-untracked analysis and lock files remain untouched.
- Recruiter validation now reports every discovered unit failure with only an
  allowlisted code, preserves valid same-provider rows, and repairs two invalid
  rows in one nine-unit regression.
- Focused runtime review passes 85 tests. Decision conformance passes its
  baseline and kills 13/13 curated mutations with no survivor or invalid result;
  source inputs remain unchanged.
- Context telemetry reported 47.8 percent remaining, so this reviewed source
  slice requires a clean substantive and ledger checkpoint before the fast
  production spine.
- The exact checkpoint is substantive commit `9f3d72a` plus ledger
  `fdf4a36`.
- Named fast Python spine: 675 passed, 6 skipped. Dashboard UI: 109 passed
  after the outer sandbox's expected `spawn EPERM` required the authorized
  rerun. Routing evaluation 1.3.0 passed every gate; routing p95 was 3.725 ms
  and cache-hit p95 was 0.989 ms.
- PR 184 merged normally as `dbd5502847b822825c7f3b99a18662949c98de0b`.
  Hosted jobs were refused before repository steps by GitHub account billing.
- Exact build `0.1.0+gdbd5502847b8` is installed. Codex refresh install is
  `0614affa-9f9d-44ea-b1e2-60e5485a3a22`; ZCode refresh install is
  `486be569-74d9-4c6b-a61f-6334762e4cd5`.
- Final trial `ar203-dbd5502-ordinary-01` is terminal `NO-GO` and will not
  be rerun under the completed one-canary authorization.

## completed-evidence

- Trial prompt hash is
  `c2618e10519afb3ff610bb0fb54d063d0e4c731481a21d4b06ea1969e9162174`;
  trace is `019fb356-a245-7c40-897e-1f89bea151b5`; session is
  `019fb356-a1c7-7ca1-94dd-ce6ea9d355d8`.
- The exact activation snapshot is schema
  `agency.canary-activation-evidence.v1`, `proven: true`, and resolved the sole
  route and parent run.
- Planner call 1 applied. Recruiter calls 2 and 3 were both rejected as
  `provider_response_contract_invalid`. Requested and resolved model was
  `gpt-5.6-luna` through `codex-subscription`; route latency was 114200 ms.
- The route planned nine units, evaluated 272 workers, retained 53 eligible,
  and correctly abstained with zero selected, loaded, delegated, or hired
  workers.
- Finalization recorded `continue` for `evidence_verification`, then
  `retry_exhausted`; accepted finalizations are zero and correction count is
  null rather than zero.
- The workspace remained empty and all five product checks failed.
- The product evaluator separately consumed the wrong evidence projection and
  the fresh Codex process reported a read-only workspace policy. AR-203 records
  those harness defects; they are not reclassified as recruiter failures.

## exact-blocker

The recruiter source boundary, merge, and exact installation are complete. The
final canary did not record an Agency route, so no recruiter call occurred and
live convergence remains unproven. AR-203 owns the preceding activation and
workspace-proof boundary.

## same-task-continuity

Keep the completed recruiter boundary frozen. Do not enlarge call budgets,
revive deterministic online selection, tune unrelated roster content, or
reinterpret the final no-route canary as recruiter evidence.

## next-bounded-work-package

1. Preserve the final no-route trial and local evidence report.
2. Resolve AR-203's restricted-workspace capability and hook-start boundary.
3. Seek explicit authorization before spending any replacement canary.

## verification

~~~text
python -m pytest tests/test_workforce_inference.py tests/test_routing_correctness.py tests/test_workforce_selection_safety.py tests/test_decision_conformance.py -q -W error
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

- Configured online selection remains inference-owned.
- Persist no provider content, raw response, unknown identifier, or exception
  text.
- Keep the one-repair fast budget fixed at three total calls.
- Preserve terminal traces and owner-untracked files.
- Touch only Codex and ZCode on this machine.
