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
branch: codex/ar-199-subagent-start-consumption
evidence_commit: 34e3180e465c175b07e1b0ae3c0b14106c36cca2
minimum_ledger_commit: d1b9692fc7f41ff29f1efb4c12895982bdb5810f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161
---

# AR-199 active recovery capsule

## checkpoint

- Exact merged revision `34e3180` is installed globally and registered in
  Codex and ZCode.
- The current repair is on `codex/ar-199-subagent-start-consumption`; the
  owner-untracked analysis draft and `uv.lock` remain untouched.
- The preceding substantive and ledger pair is a clean checkpoint for the
  current bounded repair.

## completed-evidence

- Local workforce search proves relevant enabled Windows/Codex workers exist,
  including `multi-agent-systems-architect`, `python-application-engineer`, and
  `code-reviewer`.
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
- Context telemetry at 49.0 percent required a clean checkpoint before live evaluation.
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
- PR 162 merged the hiring and model-scope repair as `279ef9e`; its exact
  revision is installed and the Codex integration was refreshed without a
  trust prompt.
- The named fast Python spine passed 651 tests with 6 skips, dashboard tests
  passed 109, Ruff passed all 601 Python files, documentation checks passed,
  and a fresh isolated routing evaluation passed every correctness and
  performance gate. Hosted checks did not start because the GitHub account's
  billing or spending limit blocked every job before execution.
- PR 164 merged optional-nickname compatibility as `34e3180`; its exact install
  again completed one selected `code-reviewer` child with a valid header but no
  activation consumption or attestation.
- Bounded live capture proved this configured v0.146 surface emitted only the
  exact rooted `task_name`. Its two apparent rollout errors were the explicit
  isolated hook-trust-bypass notices, not hook failures.
- Trace `019faef8-f76b-7740-9558-462e99f4abeb` proves parent PostToolUse records
  the synthetic task lineage before SubagentStart consumes the real child UUID.
- The attachment transaction now promotes only that exact synthetic Codex
  lineage to one consumed grant and one matching real lifecycle row, including
  reciprocal activation, delegation, work-unit, and worker-run links.
- Both callback orders are covered; all 20 activation-canary tests and all 35
  activation-receipt tests pass, with two platform skips in the latter.
- Trace `019faf50-d5d7-7bf2-8c88-e1dfd791a4fe` passes source-live with no unmet
  prerequisites: one exact activation chain, bounded correction, authoritative
  accept, completed run, and valid header.
- The isolated profile does not persist a current-profile attestation by
  design; `canary_passed: true` is the scoped source-live proof.

## exact-blocker

PR 165 merged as `816db5b`; that exact install passed isolated-profile trace
`019faf64-5aee-78e0-a5ab-657f782a6175` with one complete child chain and no
trust prompt. Two ordinary tasks then required one correction each after an
invalid first-pass manager value. Source now pins the resident pair and passes
156 focused tests plus the complete fast spine; merge, exact install, trust,
and first-pass proof remain.

## same-task-continuity

Continue in this task after the recovery and ledger commits. Do not create a
new task. Rerun the live canary only after the exact merge is installed.

## next-bounded-work-package

1. Merge and exact-install the first-pass header repair.
2. Trust/restart Codex once, then prove an ordinary task needs no correction.

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
  bypass as current-profile production evidence. The isolated canary may use
  Codex's explicit noninteractive hook-trust bypass inside its private profile.
- Preserve ready-CAS atomicity; do not hand an unscoped live Store to a planner
  that can leave partial routing or workforce writes.
- Do not rerun external-provider diagnostics without explicit egress approval.
- Preserve owner-untracked files.
- Do not create tracker issues or hosted workflows without explicit
  authorization.
