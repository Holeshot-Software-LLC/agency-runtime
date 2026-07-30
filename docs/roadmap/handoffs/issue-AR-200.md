---
title: "AR-200 active recovery capsule"
status: active
category: roadmap
created: 2026-07-29
updated: 2026-07-29
tags: [handoff, workforce, hiring, mutation-testing, evidence, recovery]
related:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-200
branch: codex/ar-200-decision-conformance
evidence_commit: 22db114f43dbc994952065e28196cd1e612df40e
minimum_ledger_commit: f48a0966ba64878e693b5bdf5214be220932828e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/175
---

# AR-200 active recovery capsule

## checkpoint

- The deterministic package is demo-ready: exact content-free contractor
  diagnostics and the disposable-copy decision-conformance gate are
  implemented and verified.
- Branch `codex/ar-200-decision-conformance` starts at merged main revision
  `22db114f43dbc994952065e28196cd1e612df40e`.
- AR-199's terminal ordinary trace remains `NO-GO`; it is evidence input, not a
  run to reinterpret or repeat before deterministic gates pass.
- Owner-untracked files remain untouched.

## completed-evidence

- The confirmed live-edge reproduction was a character/byte boundary mismatch:
  schema-valid 160-character Unicode employment prose can exceed the workforce
  projection's 192-byte text bound. Only the routing projection is normalized
  and byte-bounded; the governed employment contract remains complete.
- Post-parse rejection evidence now uses stable validation-stage codes and
  tests prove raw exception content, including a planted provider secret, does
  not enter reason codes or failed-case storage.
- The `beyond-test-coverage` sabotage mechanism was assessed. Agency will use
  its mutation-sensitivity principle but not its in-place mutation/restoration
  implementation.
- Two focused review passes completed. The second found that package links
  could survive into a private copy; the evaluator now rejects symlinks and
  Windows reparse points, with 10 conformance tests passing.
- Focused behavior: 108 passed, 1 skipped, 1 expected failure.
- Final decision-conformance proof: green baseline; 5 of 5 exact mutations
  killed; 0 survivors; 0 invalid results; every anchor occurred once; monitored
  package and selected-test inputs remained unchanged.
- Named fast Python spine: 668 passed and 6 skipped. Dashboard UI: 109 passed.
  Routing evaluation: every correctness, policy, delegation, latency, and
  263/1,000/10,000-agent scale threshold passed.
- Documentation metadata and normal validation pass for 536 Markdown files.
  Strict tracker mode separately reports the inherited AR-128 through AR-198
  parity backlog; AR-200 itself matches tracker issue 175.
- Context telemetry reported 87.5 percent remaining at package bootstrap and
  53.8 percent immediately before the implementation checkpoint; the 50
  percent hard checkpoint was not required.

## exact-blocker

Merge, exact Codex/ZCode installation, and one ordinary Codex canary remain.
The canary—not deterministic tests—must prove a relevant specialist chain,
accepted finalization, model receipts, and zero header corrections.

## same-task-continuity

Continue in this task through implementation, deterministic verification,
merge, exact installation, one bounded live canary, and evidence publication.

## next-bounded-work-package

1. Create the clean implementation and worklog-ledger checkpoint.
2. Push, review, merge, and exact-install the merged revision for Codex/ZCode.
3. Run one bounded ordinary Codex canary and publish its exact evidence to the
   local shareable report.

## verification

~~~text
python -m pytest tests/test_workforce_dynamic_hiring.py tests/test_workforce_inference.py tests/test_workforce_selection_safety.py tests/test_decision_conformance.py tests/test_cli_parser_contract.py -q -W error
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
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Online specialist appointment remains inference-owned; deterministic logic
  may recall candidates or veto unsafe nominations but cannot add or reorder an
  online selection.
- Never persist provider content or raw validation exception text in routing,
  hiring, dashboard, or report evidence.
- The mutation runner may read the requested checkout but may write only to its
  private disposable copy; it must not invoke Git restoration commands.
- Baseline failure, timeout, stale anchors, collection errors, and unrelated
  test failures are terminal invalid evidence, not successful mutation kills.
- Preserve ready-CAS atomicity, hook trust, exact native-child goal validation,
  and owner-untracked files.
