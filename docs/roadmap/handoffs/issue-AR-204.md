---
title: "AR-204 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [handoff, product, dashboard, inference, activation, automation]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-204
branch: codex/ar-203-readme-story-final-proof
evidence_commit: 03dba7538779f9c1bc64a9f6e06e5dbe9581db42
minimum_ledger_commit: fe68f86e36a2f2d82ae681d02c67ae5d4a0e6a06
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189
---

# AR-204 active recovery capsule

Bounded recovery projection for making the README product story executable.
The [canonical issue](../issue-AR-204-reconcile-readme-story-contract.md) owns
acceptance; this file records only current proof and the next package.

## checkpoint

- The active goal remains `README's main story works in reality.`
- The owner resolved all nine product ambiguities on 2026-07-30.
- Commit `ffec102` implements the first bounded package: normal owner CLI and
  dashboard-service operations no longer enter the retired presence verifier.
- Commit `c8c8020` completes the second bounded package: owner dashboard
  controls dispatch through the same governed handlers while the broker stays
  read-only.
- Commit `e1451ea` completes the third bounded package: production staffing and
  exact-unit delegation require inference-owned evidence and fail closed when
  inference is unavailable or invalid.
- Commit `03dba75` completes the fourth bounded package: attended and explicit
  autonomous activation share one behavioral proof, the supported bypass is
  labeled from the exact invocation, product trials correlate the exact rollout
  and workspace write, and activation specialist identity remains inference-
  owned through durable replay.
- The fifth bounded package is source-complete: ADR-0120 supersedes response
  repair with pre-publication header construction and terminal first-invalid
  failure across Codex, ZCode, Hermes, and OpenClaw.
- Tracker [#189](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189)
  records AR-204 under `epic:product`.
- AR-143 and AR-196 are `wont_do` and explicitly superseded by AR-204; their
  historical records no longer govern current owner authority.
- Exact installed build `5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748`
  remains the last live-tested build and is not accepted as product proof.

## completed-evidence

- Owner CLI parser leaves contain no presence metadata and dispatch directly to
  their operation-specific safety boundaries.
- `dashboard service open` reaches its ownership-checked recovery handler, which
  may install, repair, start, or restart the owned service.
- Prepared roster rollback now uses owner authority while preserving frozen
  Store, database, generation, revision, activation-authority, and workforce
  identities plus in-transaction revalidation.
- Model-facing native controls remain read-only and return
  `owner_control_required`; no broker/hook/MCP authority was widened.
- Focused verification passed 708 tests with one platform skip. Ruff checked
  all Python sources, 602 files were format-current, and 559 Markdown files
  passed metadata and documentation validation.
- Production contains no architecture anchor, deterministic unit selector,
  confidence bypass, token-only fallback, or online intent enrichment path.
  Offline helper modules remain test/evaluation fixtures and are not exported
  or called by production staffing entrypoints.
- Codex registration and native trust inventory do not prove hook start, route,
  specialist injection, delegation, or finalization.
- The owner explicitly authorized Codex's supported hook-trust bypass for this
  session. Bypassed evidence must never be labeled trusted.
- The owner bearer reaches all eight dashboard mutation endpoints. Exact
  confirmation, config revision, and host/master generation payloads are
  client-tested; stale Store identity still disables affected controls.
- The broker bearer receives `403 owner control required` for every mutation
  endpoint and authority files remain byte-for-byte unchanged.
- Dashboard verification is green: 110 client tests and 145 server/auth tests,
  with three expected platform skips. Ruff, format, and diff checks for the
  changed Python boundary pass.
- Inference-only verification is green: 368 focused tests passed with one
  intentional skip. Decision conformance passed its baseline and killed all 26
  curated regressions with zero survivors or invalid mutations; source restore
  verification passed.
- The expanded activation/product/preflight spine passed 287 warning-strict
  tests with one intentional platform skip. It includes auto-discovered full-
  suite autonomous install, actual-versus-requested bypass labeling, exact
  rollout correlation, workspace-write evidence, no-hiring canary scope,
  provider receipts, bounded inferred binding persistence, and modern plan
  equality.
- Native Codex receives exact initial, updated, and post-wait final header
  snapshots. Hermes/OpenClaw call `agency.finalize` before the natural final;
  neither production adapter asks the model to revise an invalid response.
- The finalization package passed 378 warning-strict tests with five platform
  skips and a 144-test post-format regression. Ruff, format, metadata, policy,
  documentation, and diff checks passed.
- Decision conformance passed its last complete 29-mutation run with zero
  survivors or invalid mutations. Eight later mutations are manifest-tested,
  bringing the pending complete evaluator to 37 mutations.

## exact-blocker

Owner authority, inference-only staffing, activation contracts, and first-pass
header enforcement are repaired in source. Current production still lacks the
complete 37-mutation result, rendered dashboard/configuration proof, named fast
spine, exact installation, and one native Codex product trial.

## same-task-continuity

Continue in this task through bounded implementation packages. Do not dispatch
hosted Actions while GitHub spending limits prevent runner execution. Preserve
the owner-untracked analysis draft and `uv.lock`.

## next-bounded-work-package

1. Run the complete 37-mutation local decision-conformance evaluator and stop
   on the first survivor or invalid mutation.
2. Run the authenticated packaged-dashboard render plus one reversible owner
   configuration mutation and exact restoration.
3. Run the named fast spine, checkpoint, install that exact build for Codex and
   ZCode plus dashboard, then run one bypassed native Codex product trial.

## verification

~~~text
python -m pytest tests/test_cli_owner_authority.py tests/test_cli_parser_contract.py tests/test_cli_uninstall.py tests/test_codex_activation_verification.py -q -W error
python -m pytest tests/test_prepared_codex_install.py tests/test_prepared_roster_rollback.py tests/test_store_sqlite_evidence_gap_coverage_ar91.py -q -W error
python -m pytest tests/test_update_service.py tests/test_host_control.py tests/test_adapter_parity.py tests/test_security_turn_boundaries.py -q -W error
python -m pytest tests/test_dashboard_service.py tests/test_native_installer.py tests/test_release_packaging.py tests/test_cli_upgrade.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/verify_docs.py
node --test tests/dashboard_ui.test.mjs
python -m pytest tests/test_dashboard_auth_boundary_regression.py tests/test_dashboard.py -q -W error
python -m pytest tests/test_workforce_inference.py tests/test_mandatory_inference.py tests/test_routing_correctness.py tests/test_workforce_selection_safety.py tests/test_unit_assignment_selector.py tests/test_unit_aware_delegation.py -q -W error
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Dashboard and CLI parity covers supported configuration and runtime/governance
  controls, not developer-only test or evaluation commands.
- The dashboard bearer remains automatic loopback request isolation.
- Deterministic code may recall and verify but never select a specialist.
- Missing/invalid inference and malformed/corrected headers fail loudly.
- Use the supported Codex autonomous trust bypass when needed; never edit
  undocumented private trust state or claim bypassed hooks are trusted.
- One live product trial per exact installed build; correction count must be
  exactly zero.
