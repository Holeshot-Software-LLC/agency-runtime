---
title: "AR-200 active recovery capsule"
status: active
category: roadmap
created: 2026-07-29
updated: 2026-07-30
tags: [handoff, workforce, hiring, mutation-testing, evidence, recovery]
related:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-200
branch: agent/ar-200-selection-hiring-proof
evidence_commit: f02b1af6bef5eb885aca1a334bd3a1cfb1a50bf7
minimum_ledger_commit: da40797c822330e922835eb31127d481be7d98e3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/175
---

# AR-200 active recovery capsule

## checkpoint

- Work continues on `agent/ar-200-selection-hiring-proof` from merged main
  `f02b1af6bef5eb885aca1a334bd3a1cfb1a50bf7`.
- The previous exact-installed build remains
  `0.1.0+g8bb504ce3c76`; Codex bundle
  `0.1.0+codex.d6240568ca33` and ZCode are registered and enabled.
- The one prior final canary remains terminal `NO-GO`; it is evidence input,
  not a result to reinterpret.
- The bounded source repair is demo-ready after two review passes and the full
  named fast gate. Merge, exact Codex/ZCode install, and exactly one new
  ordinary canary remain.
- Owner-untracked `docs/analysis/2026-07-25-deep-audit-findings.md` and
  `uv.lock` remain untouched.

## completed-evidence

- Prior trial `ar200-8bb504c-ordinary-02`, trace
  `019fb121-2e4c-70e0-a286-7fe25fc2e5ba`, completed in 162.641 seconds with
  two successful Luna wrapper receipts. Seven of nine units had safe proposals;
  architecture and documentation were empty.
- Architecture entered hiring and returned `gap_not_proven`; documentation
  then received `task_hiring_limit_reached`. Atomic publication recorded no
  specialists or delegations, the header was absent, correction count was null,
  and all five product checks failed.
- Root cause: nomination output classified candidates but did not record
  whether inference intended `staff` or `gap`. Any structurally valid
  nomination that could not form a typed-safe team was silently converted into
  a contractor gap.
- A declined hiring analysis also consumed `max_hires_per_task`, despite no
  workforce change, and could starve the next proven gap.
- Recruiter output now requires one explicit `staff|gap` decision per unit.
  Contradictory safe-team evidence gets the same provider's one bounded semantic
  repair; deterministic code cannot invent a gap or appoint/reorder a worker.
- Only `inference-declared-gap` plus the verifier's closed safe no-team reason
  set reaches independent whole-workforce hiring analysis.
- Hiring evidence now distinguishes `hiring_inference_abstained`,
  `hiring_gap_disputed`, and `hiring_action_invalid`. Stable verified-gap
  reason codes enter the hiring prompt; provider prose does not enter evidence.
- `max_hires_per_task` now counts applied hires/amendments. Each declared unit
  remains single-attempt and each hiring analysis retains its configured call
  budget.
- Post-hire restaffing preserves the recruiter's required, acceptable,
  forbidden, and still-declared-gap semantics instead of rebuilding an
  inference-owned proposal from rankings alone.
- Focused review suite: 121 passed, 1 skipped. Named Python spine: 664 passed,
  6 skipped. Dashboard UI: 109 passed. All routing, policy, delegation, latency,
  startup, and 263/1,000/10,000-worker scale gates pass.
- Documentation metadata and normal validation pass for 538 Markdown files;
  Ruff lint/format and diff checks pass.
- Isolated decision conformance: green baseline; 9/9 exact mutations killed;
  zero survivors; zero invalid results; source inputs unchanged. New mutations
  reverse explicit staff repair and truthful hire-budget accounting.
- No provider, install, current-profile trust, or live-canary action has been
  taken in this package yet.
- Context telemetry reported 55.5 percent remaining before the full gate, so no
  threshold checkpoint was required; the forthcoming substantive/ledger pair
  is the clean demo-ready checkpoint anyway.

## exact-blocker

No deterministic blocker is known. The package still needs the named fast gate,
clean substantive/ledger checkpoint, authorized PR/merge, exact Codex and ZCode
installation, and one fresh-process product canary. If host hook trust cannot be
bypassed during install/canary, enter `waiting_for_operator` once and stop.

## same-task-continuity

Finish this package without expanding into unrelated edge cleanup. Stop at the
first real gate failure, repair only what invalidates the visible outcome, and
rerun that gate. Run exactly one new ordinary canary after deterministic gates,
merge, and exact installation.

## next-bounded-work-package

1. Complete review pass two only for unresolved material findings.
2. Run documentation checks, the named Python/dashboard/routing spine, and the
   final 9-mutation proof.
3. Commit the substantive recovery checkpoint and its exact worklog ledger.
4. Push, open and inspect the PR, merge the authorized bounded change, and
   exact-install it for Codex and ZCode.
5. Run one ordinary Codex canary and judge receipts, selected/delegated workers,
   accepted finalization, first-response header, and correction count.
6. Update the local evidence page, tracker, roadmap, and this capsule with the
   terminal scoped verdict.

## verification

~~~text
python -m pytest tests/test_workforce_inference.py tests/test_workforce_selection_safety.py tests/test_workforce_dynamic_hiring.py tests/test_decision_conformance.py tests/test_routing_correctness.py -q -W error
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

- Configured online selection remains inference-owned. Deterministic policy may
  recall or reject but cannot add, promote, or reorder a specialist.
- Never persist provider content or raw exception text in routing, hiring,
  dashboard, or report evidence.
- Mutation work occurs only in owner-private disposable copies; invalid
  execution never counts as a killed mutation.
- Preserve ready-CAS atomicity, hook trust, native-child goal validation, and
  owner-untracked files.
