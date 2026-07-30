---
title: "AR-201 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [handoff, workforce, inference, budgets, evidence, recovery]
related:
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-201
branch: agent/ar-201-default-repair-budget
evidence_commit: c604c47685b26066f1c3dc4f3b5b9764b9436e1d
minimum_ledger_commit: 94803c62f75ca83a92aa62e4632c4b1f2692af32
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/180
---

# AR-201 active recovery capsule

## checkpoint

- PR 181 merged the repair as exact main revision
  `ed4450e9cb55c656d70c94026b22f6caebbd45e1`; exact build
  `0.1.0+ged4450e9cb55` is installed.
- AR-200 trace `019fb31f-5da6-7dd0-a983-9b983f767b9f` is terminal `NO-GO` and
  will not be rerun or reinterpreted.
- A focused test reproduced the two-call failure before implementation and now
  passes with the three-call fresh default.
- Two bounded local review passes are complete. The first corrected host-refresh
  ordering so generated timeouts follow the new effective budget; the second
  found no further authority, override, or fixed-evaluation control defect.
- The operator set the persisted fast budget to three before refreshing Codex
  and ZCode. Codex bundle `0.1.0+codex.2743f1b2ec20` serializes 185-second
  hook timeouts; ZCode serializes 185000-millisecond timeouts.
- Trial `ar201-ed4450e-ordinary-01` is terminal `NO-GO` and will not be rerun.
- Work continues under AR-202 on
  `agent/ar-202-recruiter-repair-convergence`.
- Tracker issue 180 records this bounded follow-up.
- Clean checkpoint `c604c47` plus ledger `94803c6` contains the complete source,
  test, decision, roadmap, and recovery slice.
- Owner-untracked analysis and lock files remain untouched.

## completed-evidence

- The preceding AR-200 trace applied the planner, rejected the recruiter
  contract, and stopped with `workforce_call_budget_exhausted` after two calls.
- That trace recorded zero selected, loaded, or delegated specialists; zero
  spawn/wait events; no accepted finalization; zero artifacts; and five failed
  product checks.
- Fresh bundled, typed, loader, and validation defaults now agree on three fast
  calls. Balanced four and strict five remain unchanged.
- Explicit persisted two-call configuration remains authoritative.
- Generated hook timeouts derive from the effective three-call default.
- The full focused inference, configuration, installer, and conformance suite
  passes 234 tests with 1 skip.
- A tenth curated mutation reverses the fresh typed default to two and binds to
  the exact recruiter-repair regression.
- Decision conformance passes with a green baseline, 10/10 mutations killed,
  zero survivors or invalid results, and source inputs unchanged.
- Named Python production spine: 665 passed, 6 skipped. Dashboard UI: 109
  passed. Ruff lint passes and 603 files are format-clean. Documentation
  validation passes for 542 Markdown files.
- Every routing, policy, delegation, CLI-startup, latency, and
  263/1,000/10,000-worker scale gate passes. Routing p95 is 4.328 ms,
  cache-hit p95 is 1.311 ms, and throughput is 97.06 calls/second.
- The live trial recorded all three provider calls. Planner applied; recruiter
  and recruiter repair were both `provider_response_contract_invalid` through
  requested and resolved `gpt-5.6-luna` on `codex-subscription`.
- Exact trace `019fb356-a245-7c40-897e-1f89bea151b5`, session
  `019fb356-a1c7-7ca1-94dd-ce6ea9d355d8`, and prompt hash
  `c2618e10519afb3ff610bb0fb54d063d0e4c731481a21d4b06ea1969e9162174`
  are preserved. The exact activation snapshot is `proven: true`.
- The route planned nine units but selected, loaded, and delegated zero
  specialists. Finalization ended `retry_exhausted`, correction count is null,
  the workspace is empty, and all five product checks failed.

## exact-blocker

AR-201's scoped budget repair is exact-installed and live-proven reachable. The
remaining goal is blocked by two new code defects, not by human trust:
multi-unit recruiter repair did not converge (AR-202), and the product harness
used the wrong proof projection while the isolated host reported read-only
workspace policy (AR-203).

## same-task-continuity

Preserve AR-201 as terminal evidence. Continue through AR-202, then AR-203; do
not enlarge the call budget, revive deterministic online selection, or rerun
this trial.

## next-bounded-work-package

1. Update the local evidence page and tracker with the terminal trial.
2. Implement AR-202's bounded all-failure recruiter repair and mutation proof.
3. Repair AR-203's exact activation projection and trial-scoped workspace-write
   proof.
4. Run the named fast gate, merge, and exact-install Codex/ZCode.
5. Only then spend one new ordinary canary against the combined repairs.

## verification

~~~text
python -m pytest tests/test_workforce_inference.py tests/test_configuration.py tests/test_native_installer.py tests/test_decision_conformance.py -q -W error
agency eval decision-conformance --json
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_operator_presence.py tests/test_security_turn_boundaries.py -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
~~~

## constraints

- Configured online selection remains inference-owned.
- Explicit lower call budgets remain enforceable operator opt-outs.
- No provider content or raw exception text enters durable evidence.
- Run at most one new canary in this package and preserve terminal failures.
- Touch only Codex and ZCode on this machine; preserve owner-untracked files.
