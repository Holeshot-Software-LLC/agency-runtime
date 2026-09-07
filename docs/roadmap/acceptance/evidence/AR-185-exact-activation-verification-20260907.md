---
title: "AR-185 exact activation verification evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, codex, activation, owner-authority, backlog]
related:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/acceptance/issue-AR-185.md
  - docs/roadmap/handoffs/issue-AR-185.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md
supersedes: []
superseded_by: null
---

# AR-185 exact activation verification evidence

## Scope and provenance

This builder package reconciles the July record with the existing implementation
and September 7 live proof. It introduces no runtime change, provider call,
owner-profile mutation, acceptance verdict, or done flip. Source and focused
checks use main `24eede12fc80c24e7f1dd72f32514cdf591ab2a9` in the owned
`codex/ar185-activation-proof` worktree. The candidate record remains pending
until the parent publishes and freezes it for nine isolated checks.

The live result is reused, not rerun: the actual installed verification-only
Codex invocation began at 22:02:37.810132Z and finished at 22:04:42.603459Z,
exit zero. The portable [AR-404 audit](AR-404-live-header-audit-20260907.md)
records the positive report and [AR-180 correlation](AR-180-current-profile-v6-delivery-20260907.md)
records the exact child artifact, card bytes, ordering and finalization. These
repository receipts, not inaccessible private files, carry the evidence here.

## Verification scope and original criterion 2

The original criterion is preserved verbatim:

> Every neighboring shape, unknown future public or private flag, copied marker, and
> malformed timeout fails closed before handler mutation.

The canonical correction explicitly scopes this to **the exact no-bypass
verification-only slice**. ADR-0173 retains attended and invocation-scoped
bypass modes and separately admits explicit managed-policy installation.
`install --autonomous --verify-activation` is therefore a supported different
owner-controlled operation, not an invalid request that AR-185 must disable.
It is excluded from the exact no-bypass predicate and dispatch; it is validated
under its own contract in `cli/install_commands.py:132-184`. The managed
production-container mode is likewise explicit, not a verification exception.
This correction leaves the exact key set, unknown/copied-marker rejection,
timeout checks and validation-before-dispatch ordering intact.

## Authority reconciliation and original criterion 3

The original criterion is preserved verbatim:

> Prepared `install --agent codex --no-dashboard` remains a separate,
> attended mutation and cannot overlap activation verification.

The canonical correction changes only **attended mutation** to **owner-CLI
prepared mutation**. ADR-0117's Decision permits both human and autonomous
owner CLI use without a second Agency-owned human-presence ceremony. It
explicitly retains immutable preparation, ownership, confirmation, locked
revalidation, compensation and postconditions. The current implementation
keeps verification and prepared refresh separate; restoring Windows Hello or
a new generic presence exception would contradict that accepted authority.

ADR-0104's transaction design remains relevant, but its older native-presence
prescription is not the current authority policy. Its accepted metadata has
not been relabeled or presented as a formal supersession link. ADR-0077's
deterministic staffing description and ADR-0096's presence requirement are
historical superseded records. Current restricted canary staffing is
inference-owned under the existing ADR-0179 contract, with ADR-0193's bounded
newer-version admission. No new architectural decision is introduced here.

## Installed source identity

A fresh read-only checksum diagnostic used the pinned runtime manifest's
`agency_runtime/**/*.py` rows, not generated caches. It compared each row's
SHA-256 and size with the hook file, then byte-compared that file with the
installed package, `git show 08fab1c4:<path>`, and current source. The inputs
were the existing AR-348 installed package and hook runtime
`4329d76058d18eaa6b02f0b5750ff5533462064028c1178a8b5e913364774fac`.
No runtime module was imported and no profile or database was opened.

The diagnostic exited zero in 0.500974 seconds. Its module-count result is:

```json
{
  "source_commit": "24eede12fc80c24e7f1dd72f32514cdf591ab2a9",
  "manifest_python_modules": 328,
  "installed_vs_hook_mismatches": [],
  "hook_vs_manifest_mismatches": [],
  "installed_vs_08fab1c4_mismatches": [
    "agency_runtime/__init__.py",
    "agency_runtime/core/delegation_status.py"
  ],
  "installed_vs_current_mismatches": [
    "agency_runtime/__init__.py",
    "agency_runtime/cli/install_commands.py",
    "agency_runtime/core/delegation_status.py"
  ]
}
```

Thus 328/328 installed modules match the pinned hook and manifest; 326/328
match `08fab1c4`, and 325/328 match the newer source checkpoint. The first two
differences are AR-131's public `Agency.record_delegation` identifier validator
and its helper; native Store observation normalization is unchanged. They are
outside the verification coordinator's path. The additional current-source
difference is AR-407: generic install residual reporting now filters by the
resolved target hosts, after the verification branch has already returned.

AST comparison, excluding line-position attributes, found all fourteen
verification helpers identical between the installed package and current
`cli/install_commands.py`:

```text
_validate_install_mode
_validate_install_config_mode
_bounded_utf8_text
_codex_activation_identity
_bounded_unmet_prerequisites
_activation_verification_now
_parse_activation_timestamp
_fresh_activation_attestation
_final_activation_matches
_activation_verification_projection
_activation_verification_result
_render_activation_verification
_run_codex_activation_verification
_run_exact_install_special_mode
```

The `cmd_install` prefix through `if special_result is not None: return
special_result` is also AST-identical. The rest of `install_commands.py` is
**not** claimed identical. AR-407's separate fresh-wheel evidence does not
replace this live artifact's identity or imply current main was installed in
the owner profile. The later 22:29 hook refresh reused the same runtime pointer
and existing attestation; it was not another activation proof.

## Criterion source map

Paths and line anchors below resolve at the source checkpoint above. These are
builder observations, not isolated acceptance judgments.

| Criterion | Current implementation and focused evidence |
|---|---|
| 1: exact documented command | `core/codex_activation_verification.py:198-230` recognizes the exact parser shape. `cli/install_commands.py:1439-1480` invokes one current-profile canary with `require_existing_store=True`; `:1658-1666` returns before generic installation. `tests/test_codex_activation_verification.py:131-184` exercises the real CLI entry with forbidden generic dependencies. The installed positive report is separate live evidence. |
| 2: neighboring shapes fail closed | `cli/install_commands.py:132-184` validates first. The exact predicate rejects unknown fields, non-boolean flags and nonfinite/out-of-range timeout. `tests/test_codex_activation_verification.py:189-234` rejects nearby and future public/private fields. The old copied presence marker is not a current authority token: any extra field fails this same exact key-set check. |
| 3: separate prepared mutation | `core/prepared_codex_install.py:189-210` requires `no_dashboard` and excludes verification; the verification predicate requires the opposite. `cli/install_commands.py:1557-1580` dispatches the separate branches. `core/prepared_codex_install.py:1494-1537` prepares, locks, re-prepares and compares identity before publication/swap. `tests/test_prepared_codex_install.py:644-790` covers no-op and precommit drift. ADR-0117 supplies owner authority, not a presence ceremony. |
| 4: no generic installation or hiring | `cli/install_commands.py:1658-1668` returns before config/Store/install work. `core/preflight.py:452-473` skips restricted-canary catalog reconciliation; `core/selector/pipeline.py:2223-2240` omits gap hiring for the exact probe. `tests/test_codex_activation_verification.py:131-184,851-869` uses forbidden mutation doubles; `tests/test_activation_canary_contract.py:250-304` verifies inference-owned selection without hiring. |
| 5: existing trusted current WAL Store | `core/canary_proof.py:387-421` passes existing-current mode; `core/canary_backends.py:3472-3485` projects it into the child and `adapters/hooks.py:3641-3651` consumes it. `core/store/sqlite.py:929-950` requires the configured trusted current WAL Store; `:1348-1365` uses `mode=rw`, not create; `:1431-1479` inspects read-only. Tests at `test_codex_activation_verification.py:421-468,579-605,813-848` and `test_storage_parent_trust.py:764-797` cover no bootstrap/repair, process propagation and open-time identity changes. |
| 6: fresh exact proof | `cli/install_commands.py:1203-1286` binds report schema, current profile, invocation time window, fresh trace/digest, host/plugin/install/bundle identity and final trusted inspection. `tests/test_codex_activation_verification.py:265-374` rejects malformed, mismatching and stale reports. The live v4/v6 receipt below preserves concrete identities. |
| 7: bounded nonzero failures and final inspection | `cli/install_commands.py:1467-1508` catches canary failure and performs final inspection before deciding completeness; `:1550-1554` emits and returns nonzero when incomplete. `:1289-1342` bounds/sanitizes report fields. `tests/test_codex_activation_verification.py:377-418,471-577,1479-1508` covers early refusal, canary exception, malformed fields and bounded reasons. |
| 8: focused warning-strict regressions | The three exact source-check commands below passed 175, 71 and 28 tests, total 274. Forty Windows-specific cases were deselected; no complete corpus or native Windows execution is claimed. |
| 9: actual installed current-profile proof | The installed verification-only report returned exit zero with no installation and no trust bypass. The exact v4 attestation and AR-180 host-authored v6 card/finalization correlate below. This is Linux exec depth one after existing hook trust, not a newly observed TUI approval, all-harness certification, or proof for the ongoing parent. |

## CLI authority and parser checks

Executed from the owned source worktree at the checkpoint above:

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_codex_activation_verification.py tests/test_prepared_codex_install.py tests/test_cli_owner_authority.py tests/test_cli_parser_contract.py -q -W error -k 'not windows'
```

Raw stdout, exit zero:

```text
........................................................................ [ 41%]
........................................................................ [ 82%]
...............................                                          [100%]
175 passed in 2.31s
```

## Store and canary checks

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_storage_parent_trust.py tests/test_security_config_store_coverage_complete_store.py tests/test_canary_coverage_complete.py -q -W error -k 'not windows'
```

Raw stdout, exit zero:

```text
.......................................................................  [100%]
71 passed, 40 deselected in 1.31s
```

## Inference-owned activation contract checks

```bash
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_activation_canary_contract.py -q -W error -k 'not windows'
```

Raw stdout, exit zero:

```text
............................                                             [100%]
28 passed in 0.73s
```

The earlier 175/71/28 summary is not reconstructed as raw output. The three
blocks above are fresh executions on this checkpoint. They use private test
fixtures and stubbed native/model boundaries, not a new live canary. The named
fast production spine and fresh installed artifact smoke are separately
recorded in AR-407; they are not additional AR-185 tests run here.

## Existing installed live proof

The linked AR-404 positive report records `ok=true`, `complete=true`,
`installation_attempted=false`, `trust_bypass_used=false`,
`profile_scope=current-profile`, and `attestation_persisted=true`. Read-only
inspection of the existing diagnostic envelope confirms `verification_only=true`
and exit zero. This package does not turn its earlier failing diagnostics into
passes or repeat them.

| Binding | Observed value |
|---|---|
| Host | Linux x86_64, Codex CLI 0.153.4 |
| Trace | `01a07de5-15c3-7350-86c4-b38e886caa61` |
| Install | `c482c4e2-186e-4dce-9692-98bbf22f2696` |
| Bundle | `0734429d1ba57907910723b4faaf7ec50f981513dccd0502b4518399034436b2` |
| Plugin | `0.1.0` |
| Attestation contract | `agency.codex-activation-canary.v4` |
| Passed at | `2026-09-07T22:04:41.025371+00:00` |
| Proof digest | `0bf5239c2caa6ca6b98f1346d697b07ae0009c46dcebacc50dc3f867fb55c7d6` |
| Native child | `01a07de6-532b-7e10-927e-fa1b2e7cc17d` |
| Accepted parent finalization | `e14db5ed-3754-4a11-98dc-d96b38ad93e3` |

AR-180's exact correlation records one complete v6 card in host developer
record 8 at 22:04:05.696Z, before the first non-input response at
22:04:05.698Z. The child completed with exit zero. The card body's SHA-256 is
`e409b2c8b42430b9e69b1e0a93a42e8b790e6ae86c1a3e3e31c03ea0ed9820bd`.
The actual parent final SHA-256 is
`3194d3719a0e33408380eb5d61a73f264a6f8b365c576434df381e23b9abaf8f`;
it matches the sole accepted finalization before the bound attestation.

The no-bypass exact path performs the eight-event trusted-inventory preflight
in `core/canary_backends.py:3571-3629` and requires trusted final inspection
in `cli/install_commands.py:1265-1286`. Existing native trust was retained;
there was no new TUI approval this evening and none is invented here. This
package does not certify fresh native Windows, TUI/Desktop or multi-card
delivery. The original criterion 9 wording is unchanged. AR-180 also documents
that the same card occurs in parent context; this receipt does not claim
child-only placement, which is outside AR-185's exact verification boundary.

## Publication boundary

Final documentation checks use the same interpreter with `env PYTHONPATH=.`:
`scripts/docs_metadata.py --check` passes (1,231 documents),
`scripts/update_policy_availability.py --check` passes, and `git diff --check`
passes. `scripts/update_worklog.py --check` reports `worklog index is stale`.
`scripts/verify_docs.py` reports only the two existing base-ledger errors:

```text
ERROR: docs/worklog/README.md: indexed commits do not match history (missing=['24eede12'], extra=[])
ERROR: docs/worklog/README.md: inaccurate row for 24eede12
documentation validation failed with 2 error(s)
```

The pending builder rows, empty verification table, links and capsule schema
have no reported validation errors. The parent owns the merge ledger; this
worker did not alter it or claim the overall documentation gate passed.

The parent must commit the source-linked records, freeze `candidate_commit`,
and run the isolated nine-criterion verification before any completion claim.
No verdict is supplied by this builder. This package does not change the
global registry, worklog, tracker or owner configuration. Documentation gates
are checked before handoff; the base-ledger gap is reported above.
