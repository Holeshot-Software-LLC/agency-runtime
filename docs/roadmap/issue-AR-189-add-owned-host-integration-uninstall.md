---
title: "AR-189: Add ownership-bound host-integration uninstall"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [cli, host-integrations, installation, security, operations]
related:
  - docs/roadmap/handoffs/issue-AR-189.md
  - README.md
  - docs/TROUBLESHOOTING.md
  - docs/THREAT_MODEL.md
  - CHANGELOG.md
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - agency_runtime/cli/uninstall_commands.py
  - agency_runtime/core/host_lifecycle_lock.py
  - agency_runtime/core/installer_uninstall.py
  - agency_runtime/core/installer_orchestration.py
  - agency_runtime/core/installer_filesystem.py
  - agency_runtime/core/installer_zcode.py
  - agency_runtime/core/prepared_host_uninstall.py
  - agency_runtime/core/prepared_codex_install.py
  - agency_runtime/core/windows_handle_rename.py
  - tests/test_host_uninstall.py
  - tests/test_cli_uninstall.py
  - tests/test_windows_handle_rename.py
  - tests/test_native_installer.py
  - tests/test_prepared_codex_install.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-189
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-189: Add ownership-bound host-integration uninstall

## Problem

Agency Runtime can discover and install integrations for every supported host,
but it lacks one equally clear command for removing those integrations. Manual
deletion risks leaving native registration behind, deleting an unowned file,
confusing host removal with package or data removal, or giving the dashboard a
new persistent-mutation surface.

An uninstall also cannot safely mean "delete everything." Configuration, the
SQLite Store, roster and evidence history, retained backups, the installed
Python package, and the optional dashboard service have independent ownership
and lifecycle contracts. Operators need a reversible host-integration action,
not an implicit data purge.

## Current state

The bounded implementation introduces `agency uninstall` with exactly one
target selector (`--all` or `--agent <host>`) and exactly one mode (`--dry-run`
or `--confirm-plan <digest>`). A dry run inspects every selected host, proves
the managed target and native registration identities, and emits the exact
native action plan plus a SHA-256 `plan_digest`. Application recomputes the plan
and proceeds only when the supplied digest still matches.

The plan includes a nested `binding_digest` over the managed target and parent,
runtime and retention roots, install identity and version, the full prepared
launcher projection and every executable or wrapper artifact that can
participate in process creation, allowlisted host-profile environment, and
native plugin, marketplace, gateway, or ZCode facts as applicable. The outer
digest also binds the selector, canonical host order, status, and exact native
command sequence. Native plugin and marketplace provenance use a closed set of
documented path aliases; an invalid, relative, or conflicting alias
blocks instead of letting one expected alias hide contradictory evidence.
Applying a mutating plan enters the dedicated native Windows action
`uninstall.host-integrations.v1`. Its aggregate binding covers one canonical
operation UUID, selector, canonical hosts and transitions, confirmed outer plan
hash, a hash over every per-host plan binding and exact retained destination,
and fixed `runtime-data-and-marketplaces.v1` preservation and
`retained-owned-bundles.v1` recovery policies. Denial or any changed primitive
fails before host mutation.

`--all` searches the canonical supported-host inventory for a managed bundle or
installed Agency plugin; it does not treat every stale host directory or a
Codex/Claude marketplace-only registration as removable authority. Each host
is handled independently and reports exact native steps, failure stage, retained
path, operation journal, and restart requirement. A mutating run writes its
bounded owner-private intent only after native Windows authority succeeds, the
shared lifecycle lock is held, and the plan and aggregate binding have been
revalidated, but before the first host mutation. It checkpoints each completed
host under that lock; inability to record intent or a checkpoint stops work and
reports every later selected host as `not_attempted`. Operator denial writes no
intent journal. An absent integration is an idempotent no-op.

Successful uninstall unregisters or disables the exact native integration,
proves detachment, and atomically moves the unchanged ownership-proven bundle
to `~/.agency-runtime/backups/<host>/uninstall-<operation_uuid>`, the exact
destination bound before native confirmation. It does not recursively delete
or expose a purge mode. The package, Agency Runtime configuration, Store,
roster, evidence, all backups, and dashboard service remain present. Exact
host-native registration or Agency-owned handler configuration necessarily
changes, while unrelated host configuration is preserved. Codex and Claude
marketplace registrations also remain because the current install manifest
does not prove Agency created those user-configuration entries exclusively.
Hermes detachment is host-specific: the exact Agency inventory row may remain
as disabled residue after the bundle is retained, and that disabled state is
the proven postcondition rather than a false claim that Hermes deleted the row.
Every successful result emits the exact recovery command
`agency install --rollback --agent <host> --backup <retained_path>`. POSIX uses
shell-safe joining; Windows emits PowerShell's `&` call operator with every
argument single-quoted and embedded quotes doubled, so metacharacters in the
retained path cannot become operators.

## Approach

Keep uninstall narrower than installation. Select only canonical hosts with
Agency evidence, then require a strict schema-2 ownership manifest, canonical
install ID, bounded file set, exact target binding, and a real tree containing
no links, reparse points, special files, missing entries, or unexpected entries.
Bind the confirmation digest to host, target, install ID, bundle digest, status,
and native command plan. Revalidate the install ID and bundle digest immediately
before filesystem retirement.

Detach native registration before moving its source. Bind an installed Codex or
Claude plugin and its observed marketplace source to the managed path, but
retain the marketplace registration as user configuration. A mismatched or
ambiguous marketplace blocks the operation without authorizing its removal.
Marketplace-only residue is reported and ignored by `--all`; a future installer
ledger may authorize removal only after proving that Agency created the exact
entry exclusively. Require a stopped OpenClaw gateway and remove only exact
Agency ZCode handlers after two unchanged-byte checks under the shared lifecycle
lock. Those checks are fail-closed race narrowing, not a filesystem
compare-and-swap: an external process running as the same account can still
change the ZCode config between the final read and atomic replacement. Treat
unknown native state as a blocker and document that residual race rather than
overclaiming CAS. If detachment or its postcondition cannot be proven, retain
the managed tree and return a nonzero bounded recovery result.

Serialize generic mutating install, rollback, native enable/disable
toggle, prepared Codex refresh, and prepared host uninstall through one
owner-private `host-integrations.lock`; dry runs remain write-free. After native
uninstall verification, acquire that lock, rebuild current selection and plans,
and require the plan and complete aggregate binding to match before recording
intent or dispatch. On Windows, open the exact planned source directory, verify
its file identity and ownership through that handle, rename that handle to the
already-bound destination, and prove the destination still names the same
object. This closes the target-path substitution window between final validation
and rename; a failed postcondition attempts handle-bound restoration and
otherwise reports the exact retained recovery path.

Keep the command owner-terminal-only and subject its applying mode to the exact
native `uninstall.host-integrations.v1` operator-presence action. Dry-run
remains write-free. Do not add an HTTP, dashboard, MCP, hook, or
restricted-broker mutation endpoint. The dashboard may copy only the fixed
write-free preview command for use in an owner-controlled terminal.

## Dependencies

ADR-0010 owns reversible host lifecycle, ADR-0028 owns native maturity and
postcondition truth, ADR-0031 keeps dashboard-service lifecycle separate, and
ADR-0096 requires genuine operator presence for persistent mutation. ADR-0108
defines the bounded uninstall semantics. Tracker creation remains pending
explicit authorization for the outward-facing write.

## Acceptance

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

## Implementation evidence

The settled focused uninstall, parser, operator-presence, and native-asset slice
passes 287 tests in 28.86 seconds. The latest host/CLI subset passes 42 tests in
24.70 seconds after forbidden-root and journal-order hardening, with targeted
Ruff lint and format checks passing. Generic rollback, toggle, native install,
and unchanged Codex reinstall locking passes 24 selected tests in 12.82 seconds
with 91 unrelated cases deselected. The prepared Codex install-lock regression
passes in 0.75 seconds with 43 unrelated cases deselected. This evidence covers
prepared-verifier denial, stale plans and bindings, full launcher-artifact
substitution, closed-world native aliases, marketplace preservation,
deterministic retained paths and exact-backup recovery, authority-ordered
journaling, explicit `not_attempted` hosts, all five host transitions, and one
live Windows handle-bound rename. Targeted diff checks pass. Documentation
metadata, policy-availability, worklog-index, and complete link/schema validation
pass for 485 maintained Markdown files.

After the final recovery-rendering hardening, the host-only regression suite
passes 31 tests, including a retained path containing PowerShell
metacharacters. The result uses single-quoted PowerShell literals and `&`, not a
CreateProcess-style command line misrepresented as shell-safe.

This fast evidence covers the exact prepared native action, aggregate authority
binding, shared lifecycle lock across every Agency lifecycle writer,
deterministic retained destination, exact-backup recovery, and handle-bound
Windows retirement. The remaining external same-account ZCode final
read-to-replace race is explicitly residual; the two byte comparisons are not
claimed as CAS. No package uninstall, data purge,
dashboard-service mutation, host restart, tracker write, hosted workflow, full
corpus, coverage shard, or compatibility-matrix run is part of this bounded
scope. The exhaustive workflow remains manual and is not required for this
issue or demo verdict.
