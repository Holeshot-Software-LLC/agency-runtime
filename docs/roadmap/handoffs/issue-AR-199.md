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
branch: codex/ar-199-fbed-canary
evidence_commit: b8c0a8d6e089a2624d29085c97fb90f40716413c
minimum_ledger_commit: 36d2ec67810eaffe014cc08a73402146276830d3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161
---

# AR-199 active recovery capsule

## checkpoint

- PR 171 merged the ordinary selection and eligibility repair as exact commit
  `fbed63abaf739d6a863113a221c09c8cfababc40`.
- The uv tool reports exact build `0.1.0+gfbed63abaf73`; Codex bundle
  `0.1.0+codex.ae2086569c9e` is registered and enabled.
- First ordinary product trace `019fb03e-5ad6-7b70-8d22-bc8c7ee0d028` is a
  bounded `NO-GO`; repair `b8c0a8d` is source-only.
- Owner-untracked files remain untouched.

## completed-evidence

- Exact-installed isolated trace `019fb039-193d-79c2-b771-5cdd2ad86065`
  passes with one selected and loaded `code-reviewer`, one native spawn and
  wait, one completed delegation, worker exit zero, one accepted finalization,
  a valid first-pass header, and `correction_count: 0`.
- Its profile is explicitly isolated and uses Codex's hook-trust bypass; it
  does not claim current-profile trust or persist a current-profile attestation.
- Current-profile verification sees all eight hooks enabled but modified and
  stops before model invocation. That attended trust boundary remains open.
- The ordinary product trace persisted two successful Luna wrapper receipts
  and 53 eligible workers, but its nine-unit plan atomically abstained because
  `unit-architecture` had no eligible `architecture-record` / `design` owner.
- `b8c0a8d` compiles architecture-category roles correctly, anchors that unit
  to `software-architect`, and passes 50 focused tests with one platform skip.
- Local workforce search proves relevant enabled Windows/Codex workers exist,
  including `multi-agent-systems-architect`, `python-application-engineer`, and
  `code-reviewer`.
- Provider attempts are now projected into the ready evidence and committed as
  model receipts only with the winning CAS; replay does not duplicate them.
- Governed hiring now stages validated contractor state, uses it for in-memory
  staffing and hydration, and commits the case, prompt, worker, and two hiring
  receipts inside the ready transaction. CAS loss leaves no workforce state.
- The ready transaction rechecks the daily hiring limit under its immediate
  write lock. A competing hire makes the staged commit fail and roll back.
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
- Ordinary trace `019faf9a-625a-7a23-ba2d-2679a4401eb5` abstained on three
  units, attempted hiring, and required one Stop correction, so it is `NO-GO`.
- Local replay reproduced nonsensical discovery/review winners and
  `selection_margin_too_low`; it made no external provider call.
- `196dedc` anchors the same typed unit shape to
  `codebase-onboarding-engineer`, `frontend-developer`, and `code-reviewer`.
- Post-fix replay accepts all three assignments; the focused suite passes 24
  tests with one platform skip, and targeted Ruff/format/diff checks pass.
- `c02a10a` separates the explicit eligible-catalog count from unavailable
  legacy retrieval; 71 focused receipt and selector tests pass.
- The post-repair named fast Python spine passes 652 tests with 6 skips, the
  dashboard suite passes all 109 tests, and the routing evaluation reports
  `passed: true`; documentation, Ruff, format, and diff checks also pass.
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

The architecture repair is locally `GO` but not merged or exact-installed.
The first ordinary trace remains `NO-GO`; persistent-profile trust remains
attended.

## same-task-continuity

Continue in this task. Do not rerun the passing isolated activation package.

## next-bounded-work-package

1. Run the fast production spine for `b8c0a8d`.
2. Merge and exact-install it.
3. Rerun the one bounded ordinary isolated-profile product proof.

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
