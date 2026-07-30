---
title: "AR-200 active recovery capsule"
status: active
category: roadmap
created: 2026-07-29
updated: 2026-07-30
tags: [handoff, workforce, hiring, mutation-testing, evidence, recovery]
related:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-200
branch: agent/ar-202-recruiter-repair-convergence
evidence_commit: dbd5502847b822825c7f3b99a18662949c98de0b
minimum_ledger_commit: e9c006570eafa7db8814d87fe2655c1d2cea9a35
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/175
---

# AR-200 active recovery capsule

## checkpoint

- PR 179 merged the explicit inference-decision repair as exact main revision
  `57c34e609dec06b15b73ceacdd6ee8cf75c94e95`.
- Exact build `0.1.0+g57c34e609dec` is installed. Codex refresh install
  `7a0a5b57-4d8b-47d1-afd3-166803f7f871` generated bundle
  `0.1.0+codex.8bff77d9195e`; ZCode refresh install is
  `262e7e8c-4698-4e1c-8795-32cb0e8e852d`.
- The one allowed ordinary canary is terminal `NO-GO`; it is preserved and will
  not be rerun or reinterpreted.
- AR-201 is merged, exact-installed, and live-proven to fund all three calls.
  AR-202 and AR-203 merged through PR 184 and exact build
  `0.1.0+gdbd5502847b8` is installed for Codex and ZCode.
- Final trial `ar203-dbd5502-ordinary-01` is terminal `NO-GO` and will not
  be silently rerun.
- Owner-untracked analysis and lock files remain untouched.

## completed-evidence

- Focused source suite passed 121 tests with 1 skip; the named Python spine
  passed 664 with 6 skips; dashboard UI passed 109; every routing, policy,
  delegation, latency, startup, and 263/1,000/10,000-worker scale gate passed.
- Documentation, Ruff lint/format, and diff validation passed. The isolated
  decision gate killed 9/9 exact mutations with no survivors or invalids.
- PR 179 hosted jobs were refused before repository steps by GitHub account
  billing; the complete local production gate is the executable evidence.
- Trial `ar200-57c34e6-ordinary-03`, trace
  `019fb31f-5da6-7dd0-a983-9b983f767b9f`, ran from the exact install without a
  trust prompt. Codex exited zero; the evaluator ended `NO-GO` after 231 seconds.
- The trace evaluated 272 workers, found 53 eligible, and produced nine work
  unit descriptors. The planner receipt applied through the configured Luna
  wrapper; the recruiter receipt was `provider_response_contract_invalid`.
- The two attempts exhausted the installed fast budget. No third recruiter
  repair call was possible; route status was abstained with
  `workforce_call_budget_exhausted`.
- Staffing recorded zero validated units, selected/loaded/delegated specialists,
  spawn/wait events, hiring attempts, or applied changes.
- No finalization was accepted, no artifact was written, and all five product
  checks failed. All seven header fields were present on the first response,
  but correction count was unavailable and the header is not an activity receipt.
- The local evidence page is build-verified and serves the exact prompt, trial,
  prompt hash, trace/session IDs, receipts, zero activity, mutation result, and
  scoped claim boundary.

## exact-blocker

All identified source repairs are merged and exact-installed. The final
isolated run recorded no Agency route or header and did not prove effective
workspace-write. Therefore the requested live staffing, delegation, model
receipt, accepted finalization, and clean header proof remain absent.

## same-task-continuity

Do not reinterpret deterministic gates as live proof or spend another canary
without explicit authorization. Preserve inference authority, the exact
terminal JSON, and the owner-untracked files.

## next-bounded-work-package

1. Preserve the terminal AR-203 trial in the tracker and local evidence page.
2. Prove restricted-token ownership/write access for the exact trial directory.
3. Instrument the isolated hook-start boundary without weakening trust or
   sandboxing.
4. Ask the owner before any replacement ordinary canary.

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
- Deterministic policy may recall or reject but cannot add or reorder a worker.
- Persist no provider content or raw exception text.
- Preserve terminal traces, exact install identities, and owner-untracked files.
- Stop at a genuine unbypassable trust prompt; touch only Codex and ZCode.
