---
title: "AR-189 owner-CLI reconciliation and real private uninstall evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, uninstall, host-integrations, ownership, provenance]
related:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/handoffs/issue-AR-189.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - agency_runtime/core/prepared_host_uninstall.py
  - agency_runtime/core/installer_uninstall.py
  - agency_runtime/cli/uninstall_commands.py
  - tests/test_host_uninstall_live_boundary.py
  - tests/test_host_uninstall.py
  - tests/test_cli_uninstall.py
  - tests/test_cli_owner_authority.py
supersedes: []
superseded_by: null
---

# Owner-CLI reconciliation and private uninstall evidence

## Scope and source

September 7, 2026. Original private receipt source base:
`08fab1c4fb9b7f8ed167f0aa4366182960f6eada`, plus the new test-only
`tests/test_host_uninstall_live_boundary.py`. Its SHA-256 is
`17ce2f1462b8da72ede509262885129ec513f1f4e49953f41d19602169bbeba2`.
No runtime implementation is changed in this package. The new test proves
actual in-process CLI installation, planning and application into a disposable
ZCode filesystem profile; it is not an installed-wheel subprocess test, native
ZCode process invocation, or proof that already-running host processes unloaded.

Existing commit `45be7ea575c8554fc6eb21103add26f9973b42b4` removed the
unconditional unavailable-authority exception from
`_require_host_uninstall_authority`. Its exact historical subject is
“AR-228: Fail open with honest header + fix deterministic gates hiding specialists (#237)”.
The aggregate primitive validation remained. Most prior positive uninstall
tests replaced that helper, so they alone could not establish reachability.
The new private test leaves it and the real mutation chain unpatched.

This is builder evidence and a criterion-to-evidence map, not an acceptance
verdict. No all-criteria acceptance builder is prepared at this checkpoint:
native Windows clauses remain outside the current Linux proof. The separate
updated-source publication checks are recorded below; they do not relabel the
original operation IDs or artifact hashes as a new run.

## Authority reconciliation and provenance

ADR-0117 already authorizes normal owner-CLI use by either a person or that
owner's delegated autonomous agent. The exact plan digest, aggregate binding,
private lock, ownership verification, retention and postconditions remain
transactional safety controls, not a second human-presence ceremony.

Only original criteria 4, 8 and 12 need authority terminology corrected:
“native confirmation” becomes prepared owner-CLI operation binding;
native authority/denial becomes binding validation/pre-mutation refusal;
operator-presence tests become owner-authority tests. All other criteria and
all Windows-specific clauses remain. No uninstall dashboard, HTTP, MCP, hook
or broker mutation endpoint is added; this does not reinstate a general
read-only restriction on the owner dashboard's separately authorized controls.

The original canonical issue at the source base has SHA-256
`bbcf3bbe5dcb31123c90ffe43d4b7cbc9cdd0e0216d7aca20bb0a9931683e346`.
ADR-0108 at that base has SHA-256
`5b685505bdf5f7cbec9de3a132032e6680c1c68734a78cfa6279ce222c3361e5`;
ADR-0117 has SHA-256
`608026a24a12d706d42a00135bad69cdcef427672439e4dcb46fa8513f900478`.

Superseded ADR-0108 language, retained as provenance rather than current policy:

> The plan digest confirms reviewed state; it does not replace this separate OS operator-presence boundary.

The old capsule likewise required “the exact native consent interaction” for a
mutating Windows canary. That presence requirement is obsolete under ADR-0117;
actual Windows filesystem and executable safety behavior is not obsolete.

### Original twelve criteria, verbatim

- [ ] `agency uninstall` requires exactly one target selector and one of a
  write-free dry run or exact `plan_digest` confirmation.
- [ ] `--all` considers every supported host in canonical order but mutates only
  an exact ownership-proven Agency integration and ignores marketplace-only
  residue.
- [ ] A changed plan, tree/parent/runtime identity, install ID, bundle digest,
  prepared launcher or any launcher artifact, host-profile environment, native
  plugin or marketplace source/alias, gateway state, or ZCode registration
  fails closed.
- [ ] The native confirmation binds the operation UUID, selector, canonical
  hosts/transitions, outer plan hash, per-host bindings and exact retained
  destinations, and fixed preservation/recovery policies.
- [ ] Generic install, rollback, native toggle, prepared Codex
  refresh, and prepared uninstall serialize through one owner-private
  host-integrations lock; uninstall revalidates before journaling or mutation.
- [ ] Native detachment is proven before an exact managed tree is atomically
  retained at `backups/<host>/uninstall-<operation_uuid>`; on Windows the rename
  is handle-bound so a pathname swap cannot redirect retirement.
- [ ] Repeating a completed uninstall is a successful no-op, while partial
  failures retain bounded evidence and the exact `--backup` recovery command;
  Windows renders it as PowerShell-safe single-quoted literals invoked with `&`.
- [ ] A bounded owner-private operation journal records intent only after native
  authority and locked revalidation but before the first mutation, then
  checkpoints each host outcome without native output or configuration content;
  denial writes no journal and every unattempted later host is explicit.
- [ ] Hermes may retain only its exact disabled Agency inventory row; no other
  host residue or enabled Hermes row is misreported as detached.
- [ ] The Python package, Agency Runtime configuration, Store, roster, evidence,
  backups, and dashboard service are preserved, unrelated host configuration
  and Codex/Claude marketplace registrations are retained, and no purge option
  exists.
- [ ] No dashboard or other model-facing mutation endpoint is added.
- [ ] Focused host, CLI, parser, operator-presence, and documentation checks pass.

## Current criterion-to-evidence map

The numbers below match both the original and reconciled canonical order.
Existing host-contract tests use controlled native runners and often replace
the authority helper; they are not mislabeled as real native-host executions.
The new private ZCode test provides the unpatched owner-CLI reachability proof.

| Criterion | Concrete evidence and limits |
|---|---|
| 1 | Parser tests `test_uninstall_parser_requires_one_target_and_one_mode` and `test_uninstall_parser_accepts_each_host_with_a_valid_plan_digest`; CLI digest test and private proof show write-free preview, wrong-digest refusal and exact-confirm application. |
| 2 | `_target_plans`, `_has_agency_evidence` and `_replan_selection` use canonical `HOSTS` and exclude marketplace-only evidence. `test_cli_journal_callback_failure_stops_later_prepared_host` asserts every host was inspected in canonical order. The retained July live all-host preview is historical, not rerun here. |
| 3 | `_plan_binding`, `_execution_binding` and `_commit_agent_uninstall` bind exact source/executable/native facts. Focused tests reject stale plans, changed bindings, wrong private-commit digest, duplicate/conflicting plugin and marketplace aliases, live/unproven OpenClaw state and changed post-unregister marketplace state. Native Windows companion cases are skipped on Linux. |
| 4 | `_HostUninstallBinding`, `_make_binding` and `_host_uninstall_binding_primitives` retain the UUID, selector, ordered hosts/transitions, outer hash, per-host binding/destination hash and both fixed policies. The five-host transition regression inspects the binding; the private proof reaches the actual helper without replacing primitive validation. No native presence claim is made. |
| 5 | `installer_orchestration.py` uses the shared lock for install, rollback and toggle; `prepared_codex_install._install_lock` and `prepared_host_uninstall._uninstall_lock` use the same implementation. The real private proof traverses the uninstall lock; stale/binding-change regressions exercise locked re-planning. July's broader writer-lock checks remain historical, not new live concurrency measurements. |
| 6 | `_commit_agent_uninstall` proves detachment before `_retire_owned_target`. Private ZCode proof checks zero handlers, missing registration state, absent target and exact retained bytes. Windows routes to `rename_directory_handle_bound`; its two native tests require Windows and are not executed here. |
| 7 | Private application and fresh repeat plan/confirm prove successful no-op and no extra journal. Native-failure tests preserve the tree/recovery state. `test_recovery_command_quotes_shell_metacharacters` ran its POSIX branch; its PowerShell branch is not proven by that Linux result. |
| 8 | `_apply_prepared_host_uninstall` validates then locks/re-plans before its journal callback. CLI tests cover intent/applying/complete order, refusal with no intent, journal failure and explicit later `not_attempted` hosts. The private proof uses the real writer and verifies the complete exact-plan journal. |
| 9 | `_verify_uninstalled` and the Hermes transition fixture allow its exact disabled row. `test_failed_native_detachment_retains_owned_tree_for_recovery` rejects an enabled/sticky Hermes row. These are native-protocol fixtures, not an actual Hermes uninstall. |
| 10 | Private proof compares the entire retained bundle, runtime config, history and all logical Store contents, and checks unrelated ZCode config. All-host transition fixtures preserve Codex/Claude marketplaces; the parser has no purge option. Package/service preservation flags are reported, but no real installed package or running service was removed or independently exercised. |
| 11 | Read-only source inspection finds dashboard rendering/copy handlers for the fixed `agency uninstall --all --dry-run` command and no host-uninstall mutation entry in the server dashboard/MCP modules. No endpoint is added by this test/documentation-only package. This is source inspection, not a new HTTP penetration test. |
| 12 | Host/CLI package: 68 passed, two native-Windows skips. Parser/owner-authority package: 59 passed. New real-boundary proof: one passed. Final documentation integration is separately checked; no retired operator-presence module or unavailable verifier is restored. |

## Commands and results

`AR189_PYTHON` denotes the trusted development interpreter. The first two
commands are the already-completed focused proof package; the last two were
run during this evidence capture. A private `--basetemp` below a new
owner-private temporary root was used for the receipt run so its artifacts
could be retained. The test fixture, not shell HOME overrides, owns isolation.

```bash
env PYTHONPATH=. "$AR189_PYTHON" -m pytest tests/test_host_uninstall_live_boundary.py tests/test_host_uninstall.py tests/test_cli_uninstall.py -q -W error -k 'not windows' --tb=short
env PYTHONPATH=. "$AR189_PYTHON" -m pytest tests/test_host_uninstall_live_boundary.py -q -W error --tb=short -s
env PYTHONPATH=. "$AR189_PYTHON" -m pytest tests/test_cli_parser_contract.py tests/test_cli_owner_authority.py -q -W error --tb=short
env PYTHONPATH=. "$AR189_PYTHON" -m pytest tests/test_host_uninstall_live_boundary.py -q -W error --tb=short -s --basetemp "$AR189_PRIVATE_PROOF_ROOT/test-fixtures"
```

Exact final stdout lines, all exit zero:

```text
68 passed, 2 skipped in 4.98s
1 passed in 2.24s
59 passed in 0.73s
1 passed in 2.21s
```

The two host-package skips are
`test_bound_native_command_rejects_changed_cmd_companion_before_launch` and
`test_prepared_launcher_rejects_repository_controlled_companion`.
No extra native Windows execution or provider/model call was made.

## Private isolation and actual output

The fixture invokes the real CLI parser and command handlers with private
`AGENCY_CONFIG_PATH` and `AGENCY_DB_PATH`. Existing explicit `home_dir`
seams select a newly created private home for real install, planning and apply.
The runtime-control default path, launcher inspection directory and operation
journal directory are narrowly redirected to that same root. ZCode's native
binary resolver returns absent; no external native process is launched.
`private_installer_launcher` copies real package and YAML bytes into a
private namespace and only supplies those launcher paths.

No `HOME`, `CODEX_HOME`, or host-home variable is overridden. Merely setting
`AGENCY_HOME` would not have isolated all of these paths. Provider lists are
empty, Ollama is disabled, and dashboard install is explicitly opted out.

Unpatched: `_require_host_uninstall_authority`, binding primitive validation,
lifecycle locks, selection re-planning, both plan comparisons, production
config merge/removal, ownership checks, retention and journal writer. The test
asserts rather than mocks dry-run and wrong-digest write freedom.

The receipt run completed at 23:14 UTC. Complete test-emitted JSON follows;
only the disposable root string is replaced with `$PRIVATE_HOME` and
whitespace is expanded for portability. Hashes below apply to original bytes,
not to this path-normalized display.

```json
{
  "apply": {
    "complete": true,
    "dry_run": false,
    "hosts": [
      {
        "agency_configuration_removed": false,
        "backups_removed": false,
        "canary_attestation_invalidated": false,
        "changed": true,
        "complete": true,
        "dashboard_removed": false,
        "exit_code": 0,
        "host": "zcode",
        "marketplace_registration_removed": false,
        "native_steps": [
          {
            "changed": true,
            "config_path": "$PRIVATE_HOME/.zcode/cli/config.json",
            "name": "config_remove",
            "ok": true,
            "owned_handler_count": 0,
            "preserved_global_hooks_enabled": false
          },
          {
            "config_path": "$PRIVATE_HOME/.zcode/cli/config.json",
            "drifted": false,
            "enabled": false,
            "global_hooks_enabled": false,
            "name": "config_inventory_after",
            "ok": true,
            "owned_handler_count": 0,
            "registered": false,
            "state_path": "$PRIVATE_HOME/.agency-runtime/zcode-registration.json",
            "version": null
          },
          {
            "config_path": "$PRIVATE_HOME/.zcode/cli/config.json",
            "drifted": false,
            "enabled": false,
            "global_hooks_enabled": false,
            "name": "config_inventory_after",
            "ok": true,
            "owned_handler_count": 0,
            "registered": false,
            "state_path": "$PRIVATE_HOME/.agency-runtime/zcode-registration.json",
            "version": null
          }
        ],
        "ok": true,
        "package_removed": false,
        "plugin_version": "0.1.0",
        "previous_install_id": "d8ed812b-3c8b-4e40-9a1f-de8da2f86a70",
        "recovery": "agency install --rollback --agent zcode --backup $PRIVATE_HOME/.agency-runtime/backups/zcode/uninstall-9d0c34d1-70e6-450f-b1c0-c517497b45b2",
        "recovery_backup": "$PRIVATE_HOME/.agency-runtime/backups/zcode/uninstall-9d0c34d1-70e6-450f-b1c0-c517497b45b2",
        "restart_required": true,
        "retained_path": "$PRIVATE_HOME/.agency-runtime/backups/zcode/uninstall-9d0c34d1-70e6-450f-b1c0-c517497b45b2",
        "schema_version": "agency.host-uninstall.v1",
        "status": "uninstalled",
        "store_removed": false,
        "target": "$PRIVATE_HOME/.agency-runtime/host-plugins/zcode/agency-preflight"
      }
    ],
    "inspected_host_count": 1,
    "journal_path": "$PRIVATE_HOME/.agency-runtime/operations/uninstall-9d0c34d1-70e6-450f-b1c0-c517497b45b2.json",
    "ok": true,
    "operation_id": "9d0c34d1-70e6-450f-b1c0-c517497b45b2",
    "plan_digest": "0c1f59d12c83f227c8adff958e362d108d3858b1c79314f07aefe4004e83ecd7",
    "preserved": [
      "package",
      "agency-configuration",
      "store",
      "roster",
      "evidence",
      "backups",
      "dashboard-service",
      "marketplace-registrations",
      "unrelated-host-configuration"
    ],
    "schema_version": "agency.uninstall.v1",
    "selected_by": "agent",
    "selected_hosts": [
      "zcode"
    ]
  },
  "authority_and_commit_boundaries_unpatched": true,
  "dry_run_no_owned_state_changes": true,
  "initial_owned_handlers": 7,
  "install_status": "registered",
  "owner_config_and_history_preserved": true,
  "repeat_uninstall_no_owned_state_changes": true,
  "retained_bundle_exact": true,
  "roster_and_store_contents_preserved": true,
  "scope": "real private ZCode CLI install and uninstall; no native process",
  "sqlite_read_sidecars_excluded_from_byte_snapshot": [
    "agency.db-wal",
    "agency.db-shm"
  ],
  "wrong_digest_no_owned_state_changes": true
}
```

The original raw test stdout SHA-256 is
`2c0bd6ae4621163d57a6af8b1abe1f4ff2f53e47b99a54fc8b2fabcbbdd7f24c`.
The first proof used operation
`6d3a8351-9d7b-47bc-ad66-da2ee2d606a8`, plan digest
`5f1406556d63081f82e41da488896d44e7b5a2e17e93161da79a35768c780d5b`;
those are distinct from this retained receipt run, not interchangeable IDs.

## Journal, retained bytes and Store safety

Read-only inspection at 23:15:07 UTC found exactly one operation journal,
mode `0600`, 1,006 bytes, status `complete`; its only outcome is ZCode
`uninstalled` and its plan digest equals the exact confirmed digest above.
It contains bounded identities and outcome fields, not native output or
configuration contents. Dry-run and wrong-digest refusal created no journal;
repeat no-op created no additional journal.

| Recorded object | SHA-256 |
|---|---|
| Original journal bytes | `0cc4f961a0621963f047ae5ed3ad66043064cf099379a3300e4b5fb3f57717de` |
| Per-host plan binding | `b2e93d518e674bd38027a52d45ffb36fd230602f2c1425095b2e9416cee54558` |
| Owned bundle digest | `47e86c1f987fb05ecc0cc4c39b9dfb33bf8d1cbee2d383a5c72d342f257c1a9d` |
| Retained install manifest | `a40c713679fad8821d7aa262206c89a18fde08d02e623cd6f73524f35700fe5b` |
| Retained launcher manifest | `49afa4e8063bbc92d7eb1222a14c7559d3d68a61ce985679a40d89089e58091c` |
| Retained ZCode hooks | `0bcc06013f9f6a9bf56d4370922e8bab36312968e53a02c09d7c24015c62ab58` |
| Preserved runtime config | `ec79161a11d5357e86e88c6a9656e8c88e0e382b928b5eb844bc59ff9ca83c9c` |
| Preserved owner history | `9b66ae027758173e40e34946e7b7289886c767203c6c848828fc3794e43d7135` |
| Post-proof complete logical Store dump | `3c73a22bdf8eb4ee1862727c742118837aed28f053b403c862b87b9357175f7c` |

All three retained files are mode `0600`; the test compared their complete
relative-path-to-bytes map to the pre-uninstall bundle, including both
manifests. The Store hash is SHA-256 of newline-joined `sqlite3.iterdump()`
lines: 2,595 lines across 51 tables. The test compared the complete logical
dump before and after uninstall and again after repeat, including the seeded
active roster, run and import-history event. The table count is not a claim
that every table held data.

SQLite read-only inspection can materialize its two coordination sidecars
`agency.db-wal` and `agency.db-shm`. Only those exact paths are excluded from
the general byte snapshot; logical contents are still compared in full.
No statement that every byte in the private home stayed unchanged is made.
Successful uninstall necessarily changes only its owned host state and creates
retention/journal data; dry-run and wrong-digest checks compare durable owned
state before any application.

After uninstall the unrelated ZCode theme and `UnrelatedEvent` remain, global
hooks stay disabled, and the existing shared `timeoutMs: 595000` floor remains.
That timeout was installed before the comparison; uninstall does not claim to
restore all shared host settings to their pre-install value.

## Remaining work and non-claims

The current Linux package does not supply fresh native Windows executable
companion binding, directory-handle rename or PowerShell execution/rendering
evidence. Their literal criteria remain intact for the owner's Windows
machine. Historical July Windows observations remain in the canonical record
but are not relabeled as current execution.

No real Codex, Claude, Hermes or OpenClaw integration was uninstalled. Their
controlled protocol tests, the real config-only ZCode proof and a host process
unload canary are different scopes. No live owner integration should be removed
merely to obtain a receipt. No package purge, service removal, provider change,
credential change, signing, publication, exhaustive corpus or Windows job ran.

The Agency lifecycle lock excludes Agency writers, not arbitrary same-account
ZCode writers. Its final byte-read-to-replace race remains documented; this
receipt does not promote it to compare-and-swap. Normal PR publication and any
later isolated acceptance verdicts remain separate from this builder receipt.
No duplicate tracker is created for the exempt legacy record, and its registry
continues to show `in_progress`.

Original draft checks: metadata validation passes for 1,224 Markdown documents; the
new regression passes focused Ruff lint/format and `git diff --check` passes.
`verify_docs.py` reports only the inherited missing/inaccurate `08fab1c4` merge
row in the shared worklog. That same baseline error was reproduced on pristine
detached source during the AR-183 producer check. The parent owns that ledger;
the failed documentation gate is not described as passing here.

## Updated-source publication verification

The branch fast-forwarded to
`d28ccc232dcc00af0162a2409930dd272bf97b5f`, including current main `c64ce3ce`
and its faithful AR-184 merge ledger. Before/after SHA-256 checks confirmed the
inherited canonical issue, capsule, receipt and test were preserved exactly.
The test remains SHA-256
`17ce2f1462b8da72ede509262885129ec513f1f4e49953f41d19602169bbeba2`.
No production implementation is changed by this publication package.

Fresh focused command on that updated source:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_host_uninstall_live_boundary.py tests/test_host_uninstall.py tests/test_cli_uninstall.py tests/test_cli_parser_contract.py tests/test_cli_owner_authority.py -q -W error -k 'not windows' --tb=short
```

Exact stdout, exit zero:

```text
...............ss....................................................... [ 55%]
.........................................................                [100%]
127 passed, 2 skipped in 5.49s
```

Both skips are the native-Windows companion tests named above. Repository-wide
Ruff lint passes and format reports `768 files already formatted`. The
unchanged dashboard suite passes 224 tests, zero failures/skips, 227.03862ms
with `node --test tests/dashboard_ui.test.mjs`. These fresh checks are distinct
from the earlier original receipt, and neither Windows nor installed native
process evidence is inferred from them.

The named fast Python production spine in `AGENTS.md` also ran on this source
using `env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest`, the
exact 29 listed test modules, and `-q -W error`. Its final stdout, exit zero:

```text
1085 passed, 3 skipped in 69.11s (0:01:09)
```

This was the named fast spine, not the exhaustive corpus, coverage shards or
compatibility matrix. No native Windows execution was performed.

The source console entry point also passed
`env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/agency eval routing --json --no-details`
with top-level `passed: true` and every gate passing. This evaluates
deterministic candidate recall, not specialist quality or live staffing latency.
An initial `python -m agency_runtime` invocation exited before evaluation
because this package has no `__main__`; the console entry point above is the
corrected executed command, not a product failure.

Before the substantive checkpoint, metadata and
`scripts/verify_docs.py --require-tracker` pass for 1,238 Markdown files,
policy availability and whitespace pass, and the worklog index is current for
2,066 substantive commits. The next narrow ledger records this new substantive
commit and its reasoning. Full decision-conformance mutation evaluation was
not repeated for this test/records-only slice; its existing test module is
included in the fresh named spine. Parent performs final remote parity and
normal PR publication in sequence with the other prepared branches.
