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
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-204
branch: codex/ar-203-readme-story-final-proof
evidence_commit: ffec1027ad18dee38469e710cd38049c00e3c9e2
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
- The deterministic architecture-anchor helper reported by the owner is absent
  from current source, but ADR-0088 and offline fallback behavior still permit
  deterministic specialist selection.
- Codex registration and native trust inventory do not prove hook start, route,
  specialist injection, delegation, or finalization.
- The owner explicitly authorized Codex's supported hook-trust bypass for this
  session. Bypassed evidence must never be labeled trusted.

## exact-blocker

The owner CLI boundary is repaired. Current production still violates the
contract at dashboard owner/broker dispatch and UI controls, offline staffing,
native activation propagation, response correction, and rendered dashboard
proof boundaries.

## same-task-continuity

Continue in this task through bounded implementation packages. Do not dispatch
hosted Actions while GitHub spending limits prevent runner execution. Preserve
the owner-untracked analysis draft and `uv.lock`.

## next-bounded-work-package

1. Allow bounded dashboard mutations only for the owner bearer and keep the
   broker bearer read-only.
2. Restore the owner configuration/runtime/governance client controls removed
   by the read-only production gate.
3. Run focused dashboard server, auth-boundary, transaction, and UI tests.
4. Checkpoint before beginning inference-only staffing.

## verification

~~~text
python -m pytest tests/test_cli_owner_authority.py tests/test_cli_parser_contract.py tests/test_cli_uninstall.py tests/test_codex_activation_verification.py -q -W error
python -m pytest tests/test_prepared_codex_install.py tests/test_prepared_roster_rollback.py tests/test_store_sqlite_evidence_gap_coverage_ar91.py -q -W error
python -m pytest tests/test_update_service.py tests/test_host_control.py tests/test_adapter_parity.py tests/test_security_turn_boundaries.py -q -W error
python -m pytest tests/test_dashboard_service.py tests/test_native_installer.py tests/test_release_packaging.py tests/test_cli_upgrade.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/verify_docs.py
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
