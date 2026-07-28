---
title: "AR-189 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [handoff, uninstall, host-integrations, security, recovery]
related:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
  - docs/THREAT_MODEL.md
  - README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-189
branch: main
evidence_commit: e21eab3583fd02e81a10302ee71fe064d454e83d
minimum_ledger_commit: b1ecdcf1e2043853cef9e68153c67090c6060c1a
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-189 active recovery capsule

Bounded current-state projection for ownership-bound host-integration uninstall.
The [canonical issue](../issue-AR-189-add-owned-host-integration-uninstall.md)
owns the complete problem, approach, acceptance, and implementation evidence.

## checkpoint

- Branch `main` entered this package at clean substantive/ledger pair
  `e21eab3`/`b1ecdcf`; AR-189 is the current bounded substantive package and
  requires its own parent-owned substantive/ledger checkpoint before live work.
- Telemetry reported 14.5 percent remaining and requires a clean checkpoint,
  not a task transfer or an exhaustive workflow.
- Scope is host-integration retirement only. Package removal, data purge,
  dashboard-service removal, host restart, marketplace deletion, tracker writes,
  publication, and hosted workflow dispatch are excluded.
- User draft `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged
  and excluded.

## completed-evidence

- `agency uninstall` has one canonical host selector and a write-free plan or
  exact SHA-256 confirmation flow. Marketplace-only residue does not select an
  all-host mutation.
- Applying a mutating plan enters exact native action
  `uninstall.host-integrations.v1`. Its aggregate binding covers the operation
  UUID, selector, canonical hosts/transitions, outer plan hash, per-host plan
  bindings and exact retained destinations, plus fixed
  `runtime-data-and-marketplaces.v1` preservation and
  `retained-owned-bundles.v1` recovery policies.
- Generic mutating install, rollback, native enable/disable toggle,
  prepared Codex refresh, and host uninstall share one owner-private
  `host-integrations.lock`. Uninstall re-plans and revalidates its complete
  binding under that lock after native confirmation.
- Successful retirement retains the exact ownership-proven tree at
  `~/.agency-runtime/backups/<host>/uninstall-<operation_uuid>`. Windows validates
  and renames the exact opened directory handle, then proves the destination
  identity; a failed postcondition attempts bounded handle-bound restoration.
- Full prepared launcher identity covers the platform/launcher projection and
  every executable or wrapper artifact in the actual process chain. Native
  provenance accepts only closed-world documented aliases; contradictory or
  invalid aliases block.
- Native plugin registration or exact Agency-owned ZCode handlers are detached;
  Hermes alone may retain its exact disabled Agency inventory row. Every success
  reports the deterministic retained path and exact `--backup` recovery command;
  Windows uses PowerShell `&` plus single-quoted literals for every argument.
  The package, Agency Runtime configuration, Store, roster, evidence, backups,
  dashboard service, unrelated host configuration, and Codex/Claude marketplace
  registrations remain.
- A bounded owner-private journal records intent only after Windows authority and
  locked revalidation but before the first mutation, then checkpoints every
  completed outcome. Denial writes no intent; a failure stops work and reports
  every later selected host `not_attempted`. The dashboard exposes only a
  copyable dry-run command.
- The comprehensive focused uninstall/parser/operator/native-asset slice passes
  287 tests in 28.86 seconds. The latest host/CLI subset passes 42 tests in 24.70
  seconds with targeted Ruff lint/format green. Generic rollback/toggle/native
  install/unchanged-Codex locking passes 24 selected tests in 12.82 seconds with
  91 deselected; the prepared Codex install-lock regression passes in 0.75
  seconds with 43 deselected. Targeted diff checks pass. The named documentation
  gates pass for 485 Markdown files. No exhaustive workflow is required or
  authorized.
- After final recovery-command rendering, the host-only suite passes 31 tests,
  including a retained path with PowerShell metacharacters.

## exact-blocker

- The current hardened implementation and documentation are not yet represented
  by their own clean substantive/ledger commit pair. The parent task owns that
  checkpoint now that fast verification passes.
- A real mutating Windows canary requires the exact native consent interaction
  and an ownership-proven disposable integration. It must not be simulated or
  inferred from unit tests. Write-free live planning remains safe to demo.
- Tracker creation is an outward-facing write pending explicit authorization.
  The missing tracker URL does not weaken local implementation or test evidence.
- No current exhaustive corpus, coverage-shard, compatibility-matrix, hosted,
  signed-artifact, or multi-host live result exists; none is an AR-189 demo gate.
- The Agency lifecycle lock coordinates Agency writers only. An external
  same-account ZCode writer can still modify config between the final unchanged-
  byte read and atomic replacement; this residual window is not CAS.

## same-task-continuity

The telemetry threshold requires a clean durable checkpoint, then continuation
in this same task through normal compaction. It does not create, transfer, pause,
or dispatch another task and does not authorize automatic retries of human
presence.

## next-bounded-work-package

1. Create the parent-owned substantive and `docs(worklog):` ledger commits,
   preserving the user draft and unrelated work.
2. Run a fresh write-free live plan against the installed host inventory. If an
   ownership-proven disposable Windows integration and operator are available,
   perform one attended apply and prove native detachment, exact retention, and
   idempotent re-plan; otherwise record the precise live limitation without
   faking success.

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_windows_handle_rename.py tests/test_cli_parser_contract.py tests/test_cli_operator_presence.py tests/test_windows_operator_presence.py tests/test_windows_operator_presence_native_asset.py -q -W error
python -m pytest tests/test_native_installer.py -k "rollback or toggle or native_installers_register_and_enable_with_host_lifecycle or unchanged_codex_reinstall" -q -W error
python -m pytest tests/test_prepared_codex_install.py -k install_lock -q -W error
node --test tests/dashboard_ui.test.mjs
git diff --check
# Exhaustive diagnostics run only when the owner explicitly requests them.
~~~

## constraints

- Use at most the bounded focused review passes and named fast verification.
  Do not dispatch or run the exhaustive workflow automatically.
- Never treat a plan digest as operator presence, or one host's approval as
  authority for a changed operation, selector, host, transition, destination,
  or policy.
- Never delete an unowned, drifted, unexpected, marketplace-only, or ambiguous
  path or registration. Preserve all reported recovery material.
- Do not claim ZCode compare-and-swap or run uninstall alongside an external
  same-account ZCode config writer.
- Do not add dashboard, HTTP, MCP, hook, generated-host, or brokered mutation
  authority.
- No push, PR, tracker mutation, workflow dispatch, package publication, tag,
  release, signing action, or trust-store change without authorization.
