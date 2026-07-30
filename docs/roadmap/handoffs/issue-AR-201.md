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
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-201
branch: agent/ar-201-default-repair-budget
evidence_commit: 57c34e609dec06b15b73ceacdd6ee8cf75c94e95
minimum_ledger_commit: dca598cd8d6811b7407c7b32527e59a79b694431
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/180
---

# AR-201 active recovery capsule

## checkpoint

- Work continues on `agent/ar-201-default-repair-budget` from exact merged main
  `57c34e609dec06b15b73ceacdd6ee8cf75c94e95`.
- AR-200 trace `019fb31f-5da6-7dd0-a983-9b983f767b9f` is terminal `NO-GO` and
  will not be rerun or reinterpreted.
- A focused test reproduced the two-call failure before implementation and now
  passes with the three-call fresh default.
- Two bounded local review passes are complete. The first corrected host-refresh
  ordering so generated timeouts follow the new effective budget; the second
  found no further authority, override, or fixed-evaluation control defect.
- Tracker issue 180 records this bounded follow-up.
- Owner-untracked analysis and lock files remain untouched.

## completed-evidence

- The terminal trace applied the planner, rejected the recruiter contract, and
  stopped with `workforce_call_budget_exhausted` after two calls.
- The trace recorded zero selected, loaded, or delegated specialists; zero
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

## exact-blocker

No human or trust blocker is active. The focused source slice, two reviews,
documentation checks, and 10-mutation gate are complete. The named fast gate,
PR merge, exact tool install, deliberate current-profile budget update,
refreshed Codex/ZCode bundles, and one ordinary canary remain.

## same-task-continuity

Keep this package limited to making the advertised repair reachable. Do not
expand into provider-output tuning, broader latency work, or unrelated roster
cleanup. Stop once if a genuine trust prompt cannot be bypassed.

## next-bounded-work-package

1. Commit this focused repair checkpoint and its exact ledger.
2. Run the named fast production spine and final documentation checks.
3. Open, inspect, and merge the authorized PR.
4. Install the exact tool, deliberately set the local explicit fast budget to
   three, then refresh Codex and ZCode so the generated timeout matches it.
5. Run one new ordinary canary.
6. Update the local report, tracker, roadmap, and capsules with the verdict.

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
