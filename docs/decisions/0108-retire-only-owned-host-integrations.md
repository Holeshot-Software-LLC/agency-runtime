---
title: "Retire only ownership-proven host integrations"
status: accepted
category: decisions
created: 2026-07-28
updated: 2026-07-28
tags: [installation, host-integrations, security, cli, operations]
related:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/handoffs/issue-AR-189.md
  - docs/worklog/README.md
  - docs/decisions/0010-one-command-install-and-reversible-toggle.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - README.md
  - agency_runtime/cli/uninstall_commands.py
  - agency_runtime/core/host_lifecycle_lock.py
  - agency_runtime/core/installer_uninstall.py
  - agency_runtime/core/installer_orchestration.py
  - agency_runtime/core/prepared_codex_install.py
  - agency_runtime/core/prepared_host_uninstall.py
  - agency_runtime/core/windows_handle_rename.py
supersedes: []
superseded_by: null
id: ADR-0108
type: decision
deciders: [maintainers]
---

# ADR-0108: Retire only ownership-proven host integrations

## Context

The installer wires Agency Runtime into five native hosts and may separately
seed runtime state and register an optional dashboard service. Those outcomes
do not share one ownership boundary. Removing a host adapter should not imply
removing the Python package, Agency Runtime configuration, SQLite Store, roster,
evidence, backups, or dashboard service.

Native unregistration is destructive enough that a one-shot command is also
insufficient. Host inventory can change between review and application, an
installed plugin can point at another source, an owned bundle can gain an
unexpected user file, and a live OpenClaw gateway cannot be interrupted
implicitly. A model-controlled authenticated dashboard is not human authority
for any of those changes.

## Decision

Define `agency uninstall` as host-integration retirement only. Require exactly
one target selector, either all Agency-evidenced supported hosts or one named
host. Require a write-free dry run before application. The dry run emits a
SHA-256 `plan_digest` bound to the selected host, managed target, install ID,
bundle digest, nested authority binding, planned status, and native command
sequence. The nested binding covers the managed target and parent, runtime and
retention roots, plugin version, the full frozen prepared launcher projection
and every executable or wrapper artifact that can participate in process
creation, the allowlisted host-profile environment, and applicable plugin,
marketplace, gateway, or ZCode facts. Native provenance accepts only documented
closed-world path aliases. An invalid, relative, or conflicting alias
blocks the plan even when another field names the expected target.
Application accepts only `--confirm-plan <digest>`, recomputes current state,
and fails closed if the digest differs. For a mutating plan it prepares the
closed native Windows action `uninstall.host-integrations.v1`. That aggregate
authority binds a canonical operation UUID, selector, canonical hosts and
transitions, confirmed outer plan hash, a hash of each host's plan binding and
exact retained destination, and fixed `runtime-data-and-marketplaces.v1`
preservation and `retained-owned-bundles.v1` recovery policies. The plan digest
confirms reviewed state; it does not replace this separate OS operator-presence
boundary.

For all-host selection, require a managed Agency bundle or installed Agency
plugin. Ignore a Codex or Claude marketplace registration when it is the only
remaining evidence. Marketplace registration is user configuration, and the
current install manifest does not prove whether Agency created that entry or
reused a preexisting one. Remove the installed plugin when its identity and the
observed marketplace source bind to the managed source, but retain the
marketplace registration. A mismatched or ambiguous marketplace is a blocker,
not removal authority. A future install ledger may authorize removal only by
recording and revalidating exclusive creation ownership for that exact entry.

Treat a filesystem target as removable only when a bounded schema-2 ownership
manifest proves Agency Runtime, the exact host and plugin, the canonical target,
one canonical install ID, and the complete owned-file set. Reject links,
reparse points, special entries, missing entries, unexpected entries, ambiguous
paths, and identity changes. First unregister or disable the exact native
integration and prove detachment. Then atomically move the unchanged tree to
`~/.agency-runtime/backups/<host>/uninstall-<operation_uuid>`, the exact
destination already included in the confirmed host binding. On Windows, open
the exact source directory and perform validation, rename, destination proof,
and bounded restoration through the same directory handle so a pathname swap
cannot redirect the retirement. Never recursively delete it. Return the exact
recovery command `agency install --rollback --agent <host> --backup
<retained_path>` so a later unrelated backup cannot be selected accidentally.
Render POSIX recovery with shell-safe joining. Render Windows recovery for an
attended PowerShell session with `&` and one single-quoted literal per argument,
doubling embedded quotes so path metacharacters cannot be executed.

Serialize every Agency lifecycle writer through the same owner-private
`host-integrations.lock`: generic mutating install, rollback, native
enable/disable toggle, prepared Codex refresh, and prepared host uninstall.
These paths therefore cannot publish, restore, toggle, detach, or retire the
same integration concurrently. Dry-run planning remains unlocked and write-free.
After native uninstall verification, acquire the lock, recompute the complete
selection, plan, and aggregate binding, and reject any difference before intent
journaling or host mutation.

For a mutating multi-host application, write a bounded owner-private operation
journal only after the native Windows authority succeeds and the revalidated
plan is held under the lifecycle lock, but before the first host mutation. The
journal records only operation and plan identities, host/status fields, retained
paths, and failure stages; it excludes native output and configuration content.
Operator denial writes no intent. If intent cannot be recorded, mutate no host.
If a later checkpoint cannot be recorded or a host fails, stop before the next
host, report completed outcomes, and mark every later selected host
`not_attempted` rather than omitting it.

Treat Hermes' exact disabled Agency inventory row as its native detachment
postcondition; Hermes does not expose an unregister operation and the command
must not claim that row disappeared. For ZCode, validate exact Agency handlers
and perform two unchanged-byte checks before atomic replacement while holding
the Agency lifecycle lock. This narrows Agency-to-Agency races but is not a
filesystem compare-and-swap: an external same-account ZCode writer can still
change the path between the final read and replacement. Preserve that residual
risk explicitly.

There is no purge mode. Preserve the installed package, Agency Runtime
configuration, Store, roster, evidence, existing backups, dashboard service,
unrelated host configuration, and Codex/Claude marketplace registrations.
Exact plugin registration or Agency-owned ZCode handlers necessarily change.
The retained bundle is recovery material, not a claim that native registration
remains active.
Do not restart a host automatically; require a fresh host session before
claiming that already-running processes have unloaded Agency.

Keep dashboard-service removal under its existing explicit service lifecycle.
Do not add a dashboard, HTTP, MCP, hook, generated-host, or restricted-broker
endpoint for host uninstall. The dashboard may display and copy only a fixed
write-free preview command for an owner-controlled terminal. Unknown ownership,
native identity, native state, or postcondition returns a nonzero blocked or
partial result with the files retained.

## Consequences

- Operators receive a discoverable all-host inverse without conflating host
  wiring with package or data lifecycle.
- Marketplace-only residue is visible but cannot select an all-host mutation or
  be removed without a future exclusive-ownership ledger.
- A stale plan cannot authorize a changed integration, and dry-run remains safe
  for automation and remote inspection.
- Native confirmation is one operation- and policy-bound authority grant, not a
  generic installation-family receipt or a sequence of independently replayable
  per-host approvals.
- Generic install, rollback, native toggle, prepared Codex refresh,
  and prepared host uninstall cannot race one another because they share one
  owner-private lock; prepared uninstall revalidates under it.
- User-added or ambiguous content inside a purported managed tree blocks the
  whole filesystem retirement instead of being deleted or silently moved.
- Successful removal remains reversible because the exact owned bundle is
  retained at its operation-bound deterministic destination; disk usage is not
  reclaimed by this command.
- Exact `--backup` recovery names that operation-bound bundle instead of
  selecting whichever unrelated backup happens to be latest.
- Windows recovery output is directly PowerShell-safe rather than using
  CreateProcess quoting that a shell could reinterpret.
- Windows retirement follows the validated source object through an open handle,
  closing the final pathname-substitution window before rename.
- Native partial failure can leave registration detached while source files are
  still present. Structured results identify the failed step and retained state
  so a fresh plan can safely resume.
- A durable bounded journal distinguishes an interrupted all-host application
  from an unstarted one without becoming authorization to resume it. Denial
  leaves no false intent, and later hosts are explicitly `not_attempted`.
- Hermes may truthfully retain an exact disabled inventory row after detachment.
- The lifecycle lock excludes Agency writers, not arbitrary same-account ZCode
  processes; an external final read-to-replace race remains possible.
- Existing host processes may retain already-loaded code until the operator
  restarts them; filesystem and inventory postconditions do not prove process
  unload.
- Dashboard users retain observability but gain no adjacent mutation authority.

## Alternatives

- **Remove the package and runtime data too.** Rejected because package-manager,
  configuration, Store, evidence, backup, and dashboard-service lifecycles have
  separate ownership and recovery contracts.
- **Apply from `--dry-run` or a static confirmation phrase.** Rejected because
  neither binds the current managed tree and native plan at application time.
- **Delete the plugin tree recursively.** Rejected because manifest drift,
  unexpected user files, or link substitution could turn uninstall into an
  unbounded destructive operation.
- **Validate a Windows path and then rename that path.** Rejected because a
  same-account actor could substitute the pathname between the final check and
  rename; the rename must operate on the already-validated directory handle.
- **Use independent locks for install, rollback, toggle, and uninstall.**
  Rejected because two valid lifecycle transactions could otherwise race across
  the same managed target and native registration.
- **Describe the ZCode byte checks as compare-and-swap.** Rejected because the
  external config path offers no primitive that atomically compares file bytes
  and replaces the name; the residual same-account writer window must remain
  visible.
- **Offer `--purge`.** Rejected because irreversible data retention policy is
  outside host-integration removal and would make recovery semantics ambiguous.
- **Remove Codex or Claude marketplaces by their Agency name.** Rejected because
  a product-specific name does not prove that the current installer created the
  user-configuration entry exclusively.
- **Expose a dashboard apply button or mutation endpoint.** Rejected because an
  authenticated model-callable browser does not prove human presence.
- **Select every discovered harness.** Rejected because harness presence or a
  stale configuration root is not Agency ownership evidence.
