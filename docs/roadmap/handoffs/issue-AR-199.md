---
title: "AR-199 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-29
tags: [handoff, codex, routing, workforce, evidence, recovery]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-199
branch: codex/ar-199-live-selection-followup
evidence_commit: f2f901d9d85fbe63d413ccc9d3bf01c976bcee2e
minimum_ledger_commit: 6739abd0f0503ceb0e59c583cd20214e05682bfe
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161
---

# AR-199 active recovery capsule

## checkpoint

- Exact merged revision `f2f901d` is installed globally and registered in
  Codex and ZCode.
- The current repair is on `codex/ar-199-live-selection-followup`; the
  owner-untracked analysis draft and `uv.lock` remain untouched.
- Context telemetry is at 48.1 percent remaining, so this focused green slice
  is being sealed before the named fast spine and live evaluation.

## completed-evidence

- The first trusted production task proved a valid request-scoped binding for
  `agents-orchestrator` and `chief-of-staff`.
- The Store has 272 active workers, 97 runs, 85 routing decisions, zero model
  receipts, and one specialist-load row.
- A nontrivial revision turn required selection, ran two applied structured
  provider calls, planned four work units, and still produced no unit-agent
  plan. Its receipt records zero eligible workers and
  `hiring_store_unavailable`.
- Local workforce search proves relevant enabled Windows/Codex workers exist,
  including `multi-agent-systems-architect`, `python-application-engineer`, and
  `code-reviewer`.
- Source inspection proves preflight passes `store=None` to routing, so atomic
  ready commit is preserved while provider-receipt persistence and governed
  hiring are unavailable.
- The live activation canary passed hook-trust inspection, attempted one native
  spawn, and was rejected by Agency's own exact-goal validator. No retry or
  trust bypass ran.
- Provider attempts are now projected into the ready evidence and committed as
  model receipts only with the winning CAS; replay does not duplicate them.
- Governed hiring now stages validated contractor state, uses it for in-memory
  staffing and hydration, and commits the case, prompt, worker, and two hiring
  receipts inside the ready transaction. CAS loss leaves no workforce state.
- The ready transaction rechecks the daily hiring limit under its immediate
  write lock. A competing hire makes the staged commit fail and roll back.
- The Codex canary accepts the current opaque persisted spawn message only when
  its package-owned goal, parent scope, task label, and assignment already
  correlate. Ordinary goal mismatches remain denied.
- Focused verification passes: 76 routing, receipt, hiring, and canary tests;
  29 preflight-bound tests; and 7 durable-continuation tests with 6 platform
  skips.
- PR 158 merged as `2c914b7`; its exact install passed trust after the owner
  restarted Codex and approved the refreshed hooks.
- That live canary proved exact `code-reviewer` selection and prompt delivery,
  then exposed a downstream Codex decrypt failure caused by replacing the
  opaque tool input. The child rollout used `agent_message`, carried the exact
  activation plus encrypted content, and ended with no final message.
- The follow-up preserves the opaque input, injects the exact prompt only at
  the correlated child start, and consumes the grant by exact native-hook tool
  and lifecycle evidence. The parser now accepts `agent_message` and rejects
  the observed decrypt-error completion shape.
- Follow-up focused verification passes 66 hook, Store, and activation-canary
  tests; Ruff and Python compilation checks pass.
- PR 159 merged as `3382b18` and was exact-installed. After fresh owner trust,
  its live canary successfully ran one `code-reviewer` child: the encrypted
  task decoded, the child emitted a final response, and the parent completed
  one spawn plus one wait without retry.
- The verifier still rejected that successful rollout because identity and
  fallback prose surrounded the exact delivery in `SubagentStart` context.
  Strict parsing therefore included the prefix in `original_task` and the
  suffix in `prompt_body`, invalidating both hashes.
- The current slice makes the exact delivery the complete child-start context;
  unplanned children retain the identity and fallback guidance. A new test
  round-trips the full context to the canonical canary goal and immutable
  prompt. The focused activation set passes 67 tests.
- Context telemetry reported 49.0 percent remaining, so this source-and-focused-
  verification slice requires the substantive and ledger checkpoint before the
  fast spine and live evaluation.
- Fresh USB-task evidence proves workforce inference is active rather than
  absent. Two provider calls persisted `codex-subscription/gpt-5.6-luna`
  receipts, 219 workers were evaluated, none was eligible, and dynamic hiring
  declined with the opaque `contract_invalid:ValueError` code.
- The owner-selected parent task model is Sol High. Luna is the separately
  pinned workforce planner, so the old `Actual Model selected` wording was
  semantically wrong even though its receipt was genuine.
- The current source binds generated contracts to the exact causing artifact,
  lifecycle, capabilities, tools, platforms, and current host before critic and
  persistence. Natural-language artifact prose is no longer projected as a
  typed identifier.
- The hiring response schema now matches parser bounds and closed enums.
  Explicit negative boundaries such as `Do not change drivers without human
  approval` remain valid while permissive approval bypass language remains
  rejected.
- Header model projection now separates the unobservable host-selected parent,
  workforce inference, and specialist launch evidence.
- Broadened focused verification passes 177 tests with one expected xfail;
  Ruff check and format pass all 601 Python files.
- Tracker issue 161 now provides same-repository parity:
  https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161

## exact-blocker

End-to-end exact-installed Codex workforce selection is not yet proven for the
fresh USB-style gap. The local contractor and model-scope repair requires this
checkpoint, the named fast spine, merge, exact reinstall, and a fresh task that
persists a hire, specialist activation, delegation, and scoped model evidence.

## same-task-continuity

Continue in this task after the recovery and ledger commits. Do not create a
new task or rerun the live canary until focused source verification passes.

## next-bounded-work-package

1. Commit this contractor/header repair and its ledger checkpoint.
2. Run the proportional fast spine, push, open and merge the follow-up PR.
3. Reinstall that exact merge and run a bypassed isolated activation canary.
4. Run a fresh USB-style Codex task and capture resident-manager, contractor,
   specialist, delegation, and scoped model receipt evidence.

## verification

~~~text
python -m pytest tests/test_host_hooks.py tests/test_preflight_bounds.py tests/test_store_preflight_coverage_final.py tests/test_workforce_inference.py tests/test_workforce_dynamic_hiring.py tests/test_codex_activation_canary.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests/test_senior_audit_hardening.py tests/test_configuration_namespace_security.py tests/test_executable_namespace_security.py tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard_transaction_refactors.py tests/test_routing_correctness.py tests/test_workforce_hiring_contract.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_delegation_p1_correctness.py tests/test_store_turn_atomicity.py tests/test_roster_snapshot_generation.py tests/test_mcp_protocol_hardening.py tests/test_cli_parser_contract.py tests/test_cli_upgrade.py tests/test_update_service.py tests/test_native_installer.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_host_boundary_hardening.py tests/test_cli_operator_presence.py tests/test_security_turn_boundaries.py -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
~~~

## constraints

- Preserve hook trust and exact native-child goal validation; never use a trust
  bypass as production evidence.
- Preserve ready-CAS atomicity; do not hand an unscoped live Store to a planner
  that can leave partial routing or workforce writes.
- Do not rerun external-provider diagnostics without explicit egress approval.
- Preserve owner-untracked files.
- Do not create tracker issues or hosted workflows without explicit
  authorization.
