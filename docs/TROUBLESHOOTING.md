---
title: "Troubleshooting Agency Runtime"
status: active
category: operations
created: 2026-07-10
updated: 2026-07-28
tags: [operations, troubleshooting]
related:
  - README.md
  - SECURITY.md
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0067-require-configured-inference-for-selection.md
  - docs/decisions/0071-bound-native-delegation-correction.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
supersedes: []
superseded_by: null
---

# Troubleshooting Agency Runtime

Start with machine-readable evidence:

```bash
agency doctor --json
agency config show
agency config path
agency db stats --json
agency install --all --dry-run --json
agency uninstall --all --dry-run --json
```

Do not interpret a generated file as a loaded integration. The host inventory
must advance through discovery, registration, enablement, loading, and canary
evidence separately.

## Version or update status is unavailable

Start by separating installed identity, cached status, and live discovery:

```bash
agency -V
agency version --json
agency upgrade check --channel release --refresh --json
agency upgrade check --channel main --refresh --json
agency upgrade check --channel main --cached --json
```

The stable-release command returns unavailable until a non-draft,
non-prerelease GitHub release exists. That does not imply `main` is unavailable.
This repository is private during prerelease development, so live checks first
use configured `gh` authentication. Confirm `gh auth status` succeeds in the
same owner shell if anonymous HTTPS returns 404. Update discovery is bounded to
five seconds by default; use `--timeout` only within the accepted 0.1–30 second
range.

Dashboard startup schedules stale release and main checks without blocking the
runtime. Ordinary CLI startup reads only the private cache and never puts update
I/O in hook or MCP paths. A failed result is cached for one hour and a successful
result for 24 hours; use `--refresh` to bypass a fresh entry or `--cached` to
guarantee no remote access. Set `AGENCY_UPDATE_NOTICES=0` to suppress interactive
cached notices.

`different_target` is not automatically called an update for `main` or an
arbitrary ref: the installed checkout may be ahead or diverged. Review the full
commits. `local_changes` means the commit matches but tracked files differ.
`agency upgrade` only prints exact-SHA commands. Run them, if desired, in an
owner-controlled terminal and then complete the normal Codex trust/activation
steps; the dashboard cannot apply them.

A uv-managed Agency tool intentionally has no `pip` module. Current builds
validate the bounded `uv-receipt.toml` for this exact Agency tool environment,
resolve `uv` outside repository-controlled roots, and require bounded no-config
tool/bin directory probes to match the current prefix and receipt entry point
before printing an exact-SHA `uv tool install` command. Target-changing uv/XDG
environment overrides fail closed. Ordinary pip-capable environments retain the
interpreter-bound isolated-mode pip command only when pip's regular entry point
is inside the exact environment prefix and its bounded `pip --isolated
--disable-pip-version-check --version` probe succeeds. Run a displayed plan
unchanged in the same owner-controlled environment; regenerate it after any
environment change. If neither path is proven, the plan reports `unavailable`
with no command; do not add pip to the tool environment or copy a mutable
`main` command around that failure.

## Host was not discovered

Bare `agency install` (and explicit `agency install --all`) selects a host only
when its executable is on `PATH` or a current native-state marker exists. A bare
`~/.codex`, `~/.claude`, `~/.hermes`,
or `~/.openclaw` directory may be classified as `stale-config` and deliberately
ignored.

1. Run the host's own version command in the same shell.
2. Confirm the executable is on that shell's `PATH`.
3. On Windows, confirm the npm `.CMD` shim is visible to `where.exe` or
   `Get-Command`.
4. Preview an explicit target with `agency install --agent <host> --dry-run`.

Do not create an empty host directory just to force detection. An explicit
install can stage against an existing root without an executable, but it will
report `staged-not-registered`, not success.

## `host-discovered` or `staged-not-registered`

`host-discovered` means the host is present but native inventory cannot find
Agency Runtime. `staged-not-registered` means the managed files exist but the
host has not proven registration.

Run:

```bash
agency install --agent <host> --dry-run --json
agency install --agent <host> --json
agency doctor --json
```

If the real install returns `partial_failure`, preserve the reported
`backup_path` and `failed_step`. Fix the native lifecycle error and rerun; the
filesystem stage is idempotent. To restore the previous managed source:

```bash
agency install --agent <host> --rollback
```

Rollback can restore files even when a native refresh is unavailable. In that
case it reports native state as unverified and requires a host restart/check.

## Uninstall is blocked, partial, or says the plan changed

Host uninstall is intentionally a two-step owner-terminal operation. Generate a
fresh write-free plan, review every selected host and native command, then pass
the exact digest back with the same selector:

```bash
agency uninstall --all --dry-run --json
agency uninstall --all --confirm-plan <plan_digest> --json

# One host instead of every Agency-evidenced host:
agency uninstall --agent <host> --dry-run --json
agency uninstall --agent <host> --confirm-plan <plan_digest> --json
```

`confirmation_required` means the plan was absent or changed. Do not reuse an
older digest; rerun the dry run. The digest binds the selector, canonical hosts,
managed target, install identity, nested filesystem/runtime/prepared-launcher/
profile/native-state binding, planned status, and native command sequence. The
launcher binding includes every executable or wrapper artifact that can
participate in the actual process chain, not only the first command path. Native
plugin and marketplace provenance accept only documented path aliases; relative,
invalid, or conflicting aliases block even if one field is correct.
Applying a mutating plan then opens the exact native Windows action
`uninstall.host-integrations.v1`. Its confirmation binds one
operation UUID, the canonical host transitions, the outer plan and per-host
binding hashes, each exact retained destination, and the fixed
`runtime-data-and-marketplaces.v1` preservation and
`retained-owned-bundles.v1` recovery policies. Denial, malformed native output,
or any changed value fails before host mutation; do not substitute a static
phrase or another installation-family approval.

`another host integration transaction is active` means a generic mutating
install, rollback, native enable/disable toggle, prepared Codex
refresh, or host uninstall holds the shared owner-private
`host-integrations.lock`. Do not delete or replace the lock file. Let that
attended transaction finish, inspect its result, and generate a fresh dry run;
a timed-out contender receives no authority to resume or interfere with the
active transaction.

`blocked` means ownership or native state could not be proven. Common causes are
an unexpected or missing file in the managed tree, a link/reparse point, a
plugin record bound to a different source, an unavailable host CLI, incomplete
ZCode handler state, an ambiguous or mismatched marketplace source, or a
live/unknown OpenClaw gateway. A marketplace mismatch blocks the selected
integration but does not authorize deletion of that user configuration. The
command does not delete or move the tree in these cases. Stop OpenClaw through
its native procedure before generating a new plan; do not manually delete an
unexpected entry merely to make ownership validation pass.

A Codex or Claude marketplace registration without a managed bundle or
installed Agency plugin is `marketplace-only` residue. `--all` deliberately
ignores it, and uninstall does not delete it. Marketplace entries are retained
as user configuration because the current install manifest cannot prove Agency
created an entry exclusively. Inspect or remove such configuration with the
host's own attended tooling only if you independently intend that change.

`partial_failure` means at least one native or filesystem step changed state but
the host-specific detachment or retention postcondition was not proven.
Preserve `native_steps`, `failed_step`, `retained_path`, `journal_path`, and the
operation/plan identifiers. The owner-private journal under
`~/.agency-runtime/operations/`
contains bounded status metadata, not native output or configuration content.
Intent is created only after Windows authority succeeds and locked revalidation
passes, but before the first mutation; operator denial therefore has no journal.
A journal or host failure stops later selected hosts and reports each one as
`not_attempted`; it does not authorize an automatic resume. Correct the reported
problem and start again with a fresh dry run. A successfully retired bundle
remains at the exact bound destination
`~/.agency-runtime/backups/<host>/uninstall-<operation_uuid>` and may be restored
with the reported recovery command. It includes both `--agent <host>` and the
exact `--backup <retained_path>`; the explicit backup is authoritative, so do
not omit it when more than one retained bundle exists. On Windows, copy the
reported PowerShell command exactly. It uses `&`, single-quotes every argument,
and doubles an embedded quote so `&`, spaces, and other path metacharacters stay
literal; do not strip those quotes or convert it to `cmd.exe` syntax.
On Windows, retirement renames the already-validated directory handle and then
proves that destination still names the same object. A handle-bound retirement
error reports the retained path when recovery material moved; do not manually
move, delete, or replace either path before inspecting that result.

Hermes does not expose the same unregister semantics as the other plugin hosts.
After a successful uninstall its exact Agency inventory row may remain with
`enabled=false`; that disabled residue is the required detachment postcondition.
An enabled, ambiguous, duplicated, or malformed Hermes row remains a failure.

ZCode removes only exact Agency handlers while preserving unrelated entries. It
performs two unchanged-byte checks and an atomic replacement while Agency's
lifecycle lock is held, but that lock cannot coordinate an unrelated ZCode
process running as the same account. Such a process can still write between the
final read and replacement. Avoid concurrent ZCode configuration changes during
uninstall, inspect the postcondition, and do not describe this residual window
as compare-and-swap.

Uninstall has no purge mode. It preserves the Agency package, Agency Runtime
configuration, Store, roster, evidence, every backup, unrelated host
configuration, Codex/Claude marketplace registrations, and the dashboard
service. Exact native plugin registration or Agency-owned ZCode handlers are
the configuration this operation intentionally changes. Use the separate
`agency dashboard service uninstall` lifecycle only when you also intend to
remove that service registration. The dashboard can copy only the write-free
preview command; no dashboard button or HTTP endpoint can apply host uninstall.
Restart affected hosts before judging already-loaded sessions.

## OpenClaw refuses installation

The installer will not restart a live OpenClaw gateway. If the result says
`host_restart_consent_required`, schedule a maintenance window, stop the gateway
with the host's native procedure, rerun the installer, and restart it yourself.
Then use native inventory and runtime inspection to establish loaded/canary
state. Installation also refuses prereleases, versions older than `2026.7.1`,
and release lines newer than `2026.7.x`; each release line must be requalified
against OpenClaw's typed-hook and final-delivery behavior before it is enabled.
The runtime inspection step proves required hook registration only. Its
`delivery_behavior_proven: false` result is expected until a profile-bound live
canary supplies behavioral evidence.

## Registered but runtime unverified

`registered-enablement-unverified` and `enabled-runtime-unverified` are honest
cold-inventory states, not failures hidden behind success language. Restart the
host when required, exercise a harmless preflight, and inspect again. Only a
native runtime surface can promote `loaded` or `canary`; file existence cannot.

## Codex says `activation_required`

This means the plugin files are installed and registered, but Agency has not
proved that your normal Codex profile will run the hooks. Complete the secure
activation flow:

1. Run `agency install --agent codex --no-dashboard`. Agency uses Codex's native
   registration lifecycle and does not add a separate Windows Hello prompt.
2. Close every Codex terminal TUI opened before that install or refresh. An old
   TUI can approve the prior hook snapshot after the new plugin is published,
   leaving every settled hook correctly classified as `modified`.
3. Open a fresh terminal and run `codex` to start the terminal UI.
4. Choose **Trust all and continue** when its startup hook review appears. If
   it does not appear, run `/hooks` inside that fresh terminal UI and trust all
   8 Agency Runtime hook events: `SessionStart`, `UserPromptSubmit`,
   `PreToolUse`, `PostToolUse`, `SubagentStart`, `SubagentStop`, `PostCompact`,
   and `Stop`.
5. Run `agency install --agent codex --verify-activation`.

Codex Desktop's `/hooks` screen can show connector setup such as Zoom or
Twilio. That is a different surface and does not review local command hooks.
Agency does not reproduce Codex's private trust hashes or edit them directly;
attended mode always leaves approval to Codex.

The refresh transaction reports installation completion separately from
activation completion. The verification command uses the normal Codex profile
and does not pass `--dangerously-bypass-hook-trust`. It first performs a
read-only, bounded `hooks/list` inspection in the canary working directory and
requires the exact eight Agency hooks to be enabled and trusted. A
`codex_hook_trust_not_ready` result does not start the model-backed canary; close
stale TUIs, approve from one fresh terminal TUI, and retry. If approval is
missing, changed, or rejected, installation remains incomplete and prints the
same resumable steps. An isolated-profile canary is useful for package testing
but cannot establish normal-profile readiness.

For an owner-controlled fresh container or other disposable environment where
no person can approve hook hashes, use the explicit autonomous transaction:

```bash
agency install --autonomous --verify-activation --json
```

That command uses Codex's supported `--dangerously-bypass-hook-trust` option for
the exact activation invocation only. It does not edit or export persistent
Codex trust state, and its evidence says `trust_mode=autonomous_bypass` and
`trust_bypass_used=true`, never `trusted`. Auto-discovery still installs every
detected supported harness and the default dashboard; Codex must be among the
detected targets. Autonomous and attended modes must prove the same hook-start,
inference, specialist, native-child, and finalization behavior. A refused or
incomplete bypass is a named activation failure, not a trusted installation.

## `agency off` did not unregister the plugin

The persistent soft-control contract remains reversible. The owner CLI and the
owner-authenticated dashboard expose the same supported host control:

```bash
agency status --agent <host>
agency off --agent <host> --dry-run --json
agency off --agent <host> --json
agency on --agent <host> --json
```

The committed state is checked at every adapter boundary and preserves native
registration. `status` reports native enablement, runtime soft control, and
effective state separately; `unverified` is not the same as disabled. Owner
mutations retain confirmation, generation, revision, ownership, and rollback
checks. Broker, hook, MCP, and restricted brokerage identities remain
read-only. Harness installation is a separate native-lifecycle operation.

Use `agency off --agent <host> --native` only when you intend to change the
host's plugin registry. Native control requires an inventory postcondition and
may report `enablement_unverified` or a restart requirement instead of
pretending success.

## Roster rollback rejects a prepared-state mismatch

Roster rollback is an owner CLI operation and does not require the retired
Agency-owned Windows Hello helper. It prepares the exact Store identity, roster
generation, current and target revisions, activation authority, and workforce
projection, then revalidates them inside the committing transaction. A mismatch
means another writer or configuration change made the prepared plan stale.
Refresh the roster projection and rerun the explicit rollback with the current
version and hash; do not reuse old compare-and-swap values.

## A host toggle reports a generation conflict

The dormant host soft-control contract uses optimistic concurrency. Status
includes `runtime_control_generation`, and any future positive mutation may
succeed only when that generation is still current. A stale request must never
be retried automatically because doing so would overwrite a newer choice.

Refresh `agency status --agent <host>` and review the new state. Dashboard
mutation endpoints reject without dispatch, MCP exposes read-only
`agency.host_status`, and the CLI fails closed. The generation rules remain
covered as a dormant Store
contract: idempotent requests do not advance it and a real transition advances
it exactly once.

## The Agency-wide switch did not change the current conversation

First confirm the durable master state rather than a host's separate soft or
native state:

```bash
agency status
agency off --global
agency status
```

The global state is checked before new Store, correlation, routing, delegation,
model-receipt, and finalization work. It does not remove Agency instructions
that were already injected into a model's running context. Start a fresh host
session after switching off, and another fresh session after switching on, for
a clean A/B comparison.

The canonical state is `~/.agency-runtime/run/control.json`. Do not edit, move,
or delete it: missing, malformed, or unverifiable state intentionally fails
enabled. On a restricted Windows host, a direct write may be unavailable even
though the runtime can prove a canonical read-only state. The broker is
intentionally read-only. Agency has no separate presence verifier: a normal
owner CLI invocation or the owner-authenticated dashboard may perform the
governed mutation when it can reach the owner-private state. Use a dry run to
diagnose a restricted shell without changing state:

```bash
agency off --global --dry-run --json
```

The same least-privilege broker supports `agency status` and host-scoped
status when the exact restricted-token Store boundary refuses direct access.
The service must return every supported host exactly once with a validated
master and Store snapshot, but it never proxies a mutation. If status returns
a bounded broker error, inspect or restart the service; do not relax the Store
DACL:

```bash
agency dashboard service status --json
agency dashboard service restart
agency status --json
agency off --agent codex --dry-run --json
```

`--global` is a distinct scope and cannot be combined with `--agent` or
`--native`. No current dashboard path can change the switch.

## Restricted Windows CLI cannot open the Store

Keep the installed dashboard service running when Agency commands execute
inside a restricted Codex token:

```bash
agency dashboard service status --json
agency dashboard service start
agency agents list --json
agency search "incident response" --json
agency route "review this authentication design" --json
```

Direct owner-private Store access remains the normal path. Only the exact
restricted-token refusal may switch the default installed identity to the
authenticated dashboard. Agent and roster listing traverse compact bounded
pages containing only slug, name, division, enabled, and protected state.
Exact-agent lookup remains read-only. Agent enable/disable is unavailable from
the restricted model-facing process; use a normal operator boundary instead.

Search, route, explain, and policy are computed inside the dashboard service
against its full routing metadata. The restricted CLI receives only bounded
results plus the config path/revision, active Store path, and roster revision
for that operation; it never downloads a full selector catalog. If the service
reports that its open Store differs from the desired configured Store, restart
it before retrying:

```bash
agency dashboard service restart
agency status --json
```

The dashboard intentionally rejects Store-backed reads and mutations while
`store_restart_required` is true. This prevents a config edit from combining
the old SQLite identity with new activation or routing policy.

An explicit `--config` path is never redirected. Delegation, setup, arbitrary
Store calls, and generic configuration mutation are not dashboard operations;
if the restricted token cannot perform them directly, they return a controlled
nonzero diagnostic before backend execution or evidence claims. Run those
commands from an unrestricted shell owned by the same user rather than
weakening the Store DACL.

If a restricted mutation is rejected, do not weaken the Store DACL or attempt
to turn read brokerage into mutation authority. Inspect status, then use the
supported operator boundary.

## Restricted Windows scratch is unavailable

Agency first tries the normal owner-private per-user runtime root. When a
restricted Codex token cannot create it, Agency accepts only one verified host
capability below the current user's canonical Codex visualization namespace.
The current task UUID is preferred; nested Codex workers may use a bounded
lookup only when exactly one leaf matches their active restricting capability.

The parent process's in-memory capability receipt is not inherited across an
`exec` boundary. Every child reattests only the exact randomized,
thread-bound allocation it was given, including the canonical host marker,
root/parent file identities, protected DACL, and effective-token mutation
rights. A renamed, copied, ambiguous, or differently named directory fails
closed.

Do not point scratch or worktrees at the repository, `%TEMP%`, or a guessed
task directory. An unavailable or ambiguous capability intentionally fails
closed. Confirm `CODEX_SHELL=1`, a canonical `CODEX_THREAD_ID`, and a current
Codex Desktop task. Then start a fresh task so the host recreates its writable
leaf. A normal unrestricted Claude Code, Hermes, OpenClaw, or terminal process
does not depend on this Codex-specific fallback.

## Host canary is not ready or remains stale

Start with the nonmutating report:

```bash
agency host-canary <host>
```

It lists every unmet prerequisite. Hermes and OpenClaw currently reject live
execution because a proven read-only, no-tools noninteractive mode is not
available. Codex and Claude require the exact
`RUN LIVE <host> CANARY` confirmation before invoking the host.

For an Agency-off comparison, leave the plugin installed, run
`agency off --global`, and execute `agency host-canary <host> --mode
native-only --execute --confirm "RUN LIVE <host> NATIVE-ONLY CANARY"`. The
isolated profile receives the authoritative disabled state and the result passes
only with a nonempty host response, unchanged plugin registration/load request,
no valid Agency header, and zero new Agency evidence. Restore Agency with
`agency on --global` in cleanup. A mode mismatch, unreadable control, or control
generation change is a failed observation, not a native-only result.

Current Codex and Claude managed hook manifests must include both `--config` and
`--runtime-control` absolute paths. If an older bundle omits the latter, run
`agency install --refresh` before retrying. Restricted Windows hooks use the
authenticated dashboard only when direct validation of that bound control file
is impossible; confirm the dashboard service is running if the hook safely
falls back to enabled.

A Codex or Claude result is scoped to the temporary profile in which the
managed plugin was explicitly requested. It does not prove that the real host
profile is registered or enabled. The inspector therefore reports an
isolated-profile attestation as stale for real-profile maturity. Other stale
reasons identify an OS, host
version, plugin version, install ID, bundle digest, native state, or rollback
change. Re-run a live canary only after reviewing those facts; do not edit the
attestation manually.

## Product evaluation reports workspace write not proven

`agency eval product` requires an existing empty real workspace. For Codex,
the evaluator creates a disposable profile that trusts only that exact
workspace; it does not copy or edit the persistent profile's project-trust
configuration. The host remains under `--sandbox workspace-write` with no
additional write directory.

The evaluated Codex invocation must create the harness sentinel before doing
the product work. Do not create that file manually: a preexisting sentinel is a
failed trial. Missing, null, mismatched, linked, oversized, or uncleanable
evidence produces `workspace_write_not_proven` and skips product grading.
Inspect `host_execution.agency_evidence.workspace_trust`,
`workspace_write`, `product_prompt_hash`, and `executed_prompt_hash` in
the JSON report. In Agency mode the runtime evidence must also be
`agency.canary-activation-evidence.v1` for the exact executed prompt hash.

## Dashboard does not authenticate

For an installed user service, inspect it and ask the CLI to open the current
authenticated URL:

```bash
agency dashboard service status --json
agency dashboard service open
agency dashboard service restart
```

The rotating token lives only in the owner-restricted
`~/.agency-runtime/run/dashboard.json` descriptor. A forced process termination
can leave a stale descriptor, but `status` and `open` verify authenticated
reachability and never treat file existence as liveness. The token is not
present in Task Scheduler, the systemd unit, command arguments, status JSON, or
logs.

For foreground fallback, start a new process and use the exact URL it prints:

```bash
agency dashboard --no-open
```

The access token lives in the URL fragment, is removed from the visible URL,
and expires when the process stops. An old tab cannot authenticate to a new
process. The server rejects non-loopback `Host` values and cross-origin
requests. Do not bind or proxy the dashboard to another interface.

If the port is busy, omit `--port` to select a free one or choose another
loopback port. The service uses `dashboard.port` (7810 by default); change it
through Settings or `agency config set dashboard.port <port>`, then restart the
service.

## Dashboard live updates pause or reconnect

The Signal Observatory polls only while its tab is visible and the Live control
is enabled. A hidden tab intentionally shows a paused state and refreshes as
soon as it becomes visible. If the control says `Live updates paused`, enable
it directly in the dashboard.

Transient local-server or database errors use capped retry backoff. An expired
or rejected token is terminal: the dashboard will not retry it indefinitely.
Run `agency dashboard service open` (or start a new foreground process) to
obtain a fresh authenticated session. Live polling reads bounded metadata only;
it does not repeatedly inspect native hosts or overwrite an edited Settings
form.

The roster Operations filters, quarantine Review queue, and inference Provider
chain are bounded operational views, not continuous external probes. `remote
freshness unverified` means no separate upstream status/sync operation supplied
fresh evidence. Provider readiness plus recent persisted routing/model receipts
does not prove that an endpoint is reachable now. Run the relevant CLI status,
audit, or sync command deliberately before treating either view as live proof.

## Dashboard service does not install or start

After changing Agency's Python environment, `agency dashboard service status
--json` may report a valid older immutable worker as inactive and
`repair_recommended`. Read-only inspection verifies that worker against its own
recorded interpreter and package hashes; it does not run the worker through the
new CLI's Python. Use an attended `agency dashboard service install` to replace
the registered worker. Do not rewrite the manifest, scheduled task, or Python
path by hand.

Preview the exact current-user plan:

```bash
agency dashboard service install --dry-run --json
```

On Windows, confirm Task Scheduler is available to the current account. On
Linux, `systemctl --user show-environment` must succeed; Agency Runtime does not
silently install cron jobs, shell-profile launchers, or enable lingering. WSL
installations without a working systemd user manager should use foreground mode
or rerun installation with `--no-dashboard`. Do not work around the error by
installing a system-wide or administrator-owned service.

On WSL with a working systemd user manager, Agency positively identifies the
WSL kernel and omits only `PrivateTmp` from the generated user unit. WSL's
private-tmp mount namespace can expose root-owned configuration ancestors as
overflow UID `65534`, which the worker correctly rejects. Agency does not relax
that path-trust check: `NoNewPrivileges`, `UMask=0077`, restricted address
families, loopback binding, authentication, and owner-private runtime paths stay
enabled. Normal Linux and unknown environments retain `PrivateTmp=true`.

If the diagnostic lists non-durable manager environment names, remove them from
the systemd user manager with `systemctl --user unset-environment NAME` and
persist non-secret settings in `agency.yaml`. Values are intentionally never
shown. An absolute `XDG_CONFIG_HOME` must also have a real owner-safe ancestor
chain; Agency will not fall back to another unit path when that namespace is
unsafe.

Removal is explicit and idempotent:

```bash
agency dashboard service stop
agency dashboard service uninstall
```

Uninstalling the service leaves configuration, SQLite data, roster state, host
integrations, and packaged dashboard assets intact.

## MCP client cannot start Agency Runtime

Test the executable in the same environment as the MCP client:

```bash
python -m agency_runtime.server.mcp --stdio
```

The process waits for MCP JSON-RPC on standard input, so no banner is expected.
Generated host bundles use the absolute interpreter path captured during
installation. Reinstall the bundle after moving or deleting the virtual
environment. Protocol logs belong on standard error; any human text on standard
output breaks framing.

## Finalization reports terminal or invalid correlation

Do not resend the same draft with the same `trace_id` after
`AGENCY TURN TERMINAL` or `AGENCY CORRELATION INVALID`. A terminal trace is
immutable and cannot become the current turn again. Run a fresh Agency preflight
for the next real external user turn or exact child assignment and carry the new
`session_id`/`trace_id` through every load, skill, delegation, model, and
finalization call.

Current header enforcement does not request Stop correction. Agency supplies or
constructs the exact Store-backed header before first publication. The first
missing, malformed, stale, or evidence-mismatched natural response closes as
`response_invalid`, or `delegation_declined` for unresolved strongly preferred
delegation, and cannot be retried on that trace. Historical `retry_exhausted`
rows remain readable only for earlier builds. Planned units that the host skips
or declines need truthful nonexecution receipts, not fabricated specialist
activations.

If a host repeats terminal-correlation feedback after a fresh preflight, its
generated bundle may be older than the installed runtime. Inspect registration
and launcher identity, reinstall that host integration, then start a fresh host
session. Do not delete SQLite history or edit trace rows to break the loop.

## LiteLLM callback is not active

Importing `agency_runtime.adapters.litellm` does not mutate LiteLLM's registry.
For SDK use, call `register_litellm_callback()` in every worker and inspect its
`registered` and `reason` fields. For LiteLLM Proxy, configure:

```yaml
litellm_settings:
  turn_off_message_logging: true
  callbacks: agency_runtime.adapters.litellm.callback.proxy_handler_instance
```

Also confirm `adapters.litellm.enabled` is not `false`, the proxy is reachable,
and the configured key can access its model endpoint. Use `agency doctor`; do
not treat a successful Python import as gateway activation.

When callback registration omits an explicit config object, the callback reloads
the file-aware config bound to its Store for each event. CLI or dashboard
changes to adapter enablement, disabled agents, skipped models, capture policy,
or routing policy take effect on the next event. Passing a config object to the
callback opts into an immutable snapshot instead.

If the response header shows the actual model as unavailable, inspect the
callback payload available from the installed LiteLLM version. Agency keeps the
requested alias, `model_group` router name, provider, and response model
separate. It prefers provider response telemetry, then LiteLLM's resolved
provider/model metadata; it never upgrades the requested alias or opaque
deployment ID into an actual-model claim. A verified `model_group` remains
visible as `via LiteLLM router <name>` even when the actual model is
unavailable or the request failed. Failed requests remain unavailable even if
their payload contains success-shaped model fields.

## CLI judge is installed but unavailable

Run the host's read-only status commands, then compare them with `agency
doctor --json`:

```bash
codex login status
codex exec --help
claude auth status
claude --version
agency doctor --json
```

Codex must expose the non-interactive JSON, output-schema, ephemeral,
rule/config isolation, strict-config, and sandbox controls. Claude must be
version 2.1.205 or newer for the required structured-output failure behavior.
An executable can therefore be `installed: true` while `authenticated` or
`usable` remains false. Reauthenticate with the host CLI or upgrade it; do not
copy its session credential into Agency Runtime configuration.

Provider order is exact and supports at most four entries. A nonempty
`providers` list is authoritative, so include every desired HTTP, CLI, or local
fallback explicitly. After the last configured entry fails on a turn that
requires selection, Agency records an explicit degraded result and does not
label deterministic candidates as inferred; a removed legacy judge or Ollama
endpoint is not retried.

Credentialed remote provider URLs must use HTTPS. Plain HTTP is supported only
for literal loopback addresses such as `127.0.0.1`, `::1`, or `localhost`.
Remove embedded credentials, query strings, and fragments from `base_url`; use
the typed key or environment-key fields instead.

If delegation reports that owned descendants outlived the parent, the runtime
terminated the entire Windows Job Object or Linux subreaper-owned tree and
rejected the result. Fix the backend command so it waits for its children and
closes inherited standard-output and standard-error handles before exiting.

Linux delegation also fails closed when `/proc`, the pre-opened children
descriptor, `prctl` subreaper support, `pidfd_open`, or pidfd signaling is
unavailable. Use a supported native Linux kernel with `/proc` mounted; do not
replace the containment failure with an unowned process-group fallback.

## The remediation queue reports unvalidated resolution records

Inspect the bounded queue projection:

```bash
agency roster remediation queue --limit 50
```

`unvalidated_resolution_count` means raw resolution audit rows exist without a
current HMAC-verified, dependency-complete authority marker. Those rows do not
suppress pending work. This can be expected after evidence mutation, an
interrupted older import, or adversarial duplicate insertion. Rerun the normal
source import so the runtime can validate current evidence and append or reuse
one unambiguous canonical resolution. Do not hand-edit a marker or delete
quarantine evidence to make the count disappear. For a genuinely new repair,
follow the exact-hash maintainer remediation workflow in the README; unknown or
ambiguous input must remain queued.

## Inference is configured but routing is degraded

Inspect configuration, current diagnostics, and the dashboard's inference view:

```bash
agency config show
agency doctor --json
agency explain "describe the concrete task" --session-id debug
```

Configured inference is mandatory for conversation, new intent, revision, and
any continuation that must reroute. The provider chain is tried in declared
order within one bounded budget. Authentication failure, timeout, malformed
output, an invalid selection, or exhaustion keeps the decision degraded. The
`UserPromptSubmit` boundary blocks the substantive prompt before parent-model
generation; Agency does not fall through to its steward or the host generalist.
The dashboard lists configuration
readiness and recent persisted failures, but intentionally performs no live
provider probe.

Repair or reorder the configured providers, then rerun a fresh preflight. If no
provider is configured, configure one before submitting a substantive task;
Agency has no deterministic specialist-selection mode. Do not leave a broken
provider configured in the hope of obtaining a silent fallback. Candidate
audit with `--require-inference` is also fail-closed: a degraded inference
review cannot approve or activate a quarantined revision.

## No specialist is selected

A proven pure acknowledgement can intentionally bypass specialist selection.
Every other selection-requiring turn first infers the ideal specialist from an
open-ended role pool. It either accepts a faithful roster match or declares a
gap and attempts to create a narrow contractor. If neither path produces an
accepted specialist, the prompt fails loudly. Inspect the active roster and
decision receipt:

```bash
agency roster list
agency policy --json
agency explain "describe the concrete task" --session-id debug
```

If the roster is empty, run `agency install` to seed missing starter agents or
activate an approved roster snapshot. Check disabled, quarantined, retired,
host/tool-ineligible, and conflict-rejected candidates before assuming retrieval
failed. If inference is missing or its provider chain fails, the decision must
remain visibly degraded with no selected, recommended, delegated, or hired
specialist. Deterministic candidate recall may explain which shortlist boundary
was inspected, but it cannot become a team. The protected `agency-steward`
records the failed evidence boundary; it cannot answer, select, or act as a
semantic domain match.

`agency policy --json` exits nonzero when a required bundled specialist is not
active or a route is not classified. `missing_enabled` identifies required
specialists that `agency install` can restore. `disabled_routes` are different:
they are intentionally roster-gated, include a reason, and become eligible only
after the named specialist passes roster approval and activation. Validate that
the checked-in availability registry matches every action and division route
with:

```bash
python scripts/update_policy_availability.py --check
```

If a specific governed agent is missing, inspect the reversible activation
policy before changing roster state:

```bash
agency agents list
agency agents list --json
agency agents enable <slug>
```

The JSON response includes the exact `config_path`. CLI and dashboard must point
to that same identity. All governed agents are enabled by default, but an
operator-disabled slug is excluded from new routing, search, prompt loads, and
affected turn completion until it is re-enabled. `agents-orchestrator` and
`chief-of-staff` are imported optional specialists and can be disabled. The
parent-only `agency-steward` is protected infrastructure and is not a selectable
roster row.

## A custom companion policy is refused

Check `companion_policy_path` or `AGENCY_POLICY_PATH` and inspect the named file
without replacing or weakening its parent directory. A present custom policy
must be a regular file owned by the current operating-system user, have exactly
one hard link, and remain the same file during the read. Other POSIX accounts
may read it but must not have group or other write permission. On Windows, the
owner must be the exact current user and the effective DACL must prove that no
other account can mutate it. Symlinks, reparse points, hard links, owner drift,
identity swaps, and indeterminate access checks fail closed.

If no override is intended, remove the setting and the default
`~/.agency-runtime/companion_policy.yaml`; Agency then uses its bundled policy.
Do not copy a policy through a shared or cross-account-writable namespace merely
to bypass the check. After fixing ownership or permissions, rerun:

```bash
agency policy --json
agency eval routing --json --no-details
```

## Delegation remains suggested or skipped

A suggestion is not proof that a host delegated. Confirm the host called a
recognized delegation tool and that its result indicates success. Failures,
timeouts, malformed structured output, unavailable executables, and failed
prerequisites remain `skipped` or `failed`. Check the work-unit identity in the
evidence view or SQLite record rather than matching only the agent name.

The generic backend is unavailable until configured with an explicit command.
That is intentional; it never turns a no-op into completed work.

Each detected work unit has its own compatible specialist closure; do not assume
the first parent specialist owns every unit. Unit routing considers the complete
approved enabled roster and uses configured inference when semantic selection
is required. A unit with no eligible match remains unmatched—protected resident
managers coordinate the parent and are never substituted as domain workers.

Selection is still only a plan. The native host may refine, merge, schedule, or
decline units. Only units it actually starts require one-use child activation
and reciprocal native worker/run evidence; skipped, declined, or
retry-exhausted units close as nonexecution. Dependents enter the ready queue
only after every one of their own prerequisites has an authoritative successful
result. A slow independent unit no longer blocks a ready branch, but a failed,
missing, duplicate, or malformed prerequisite recursively skips its descendants.
Inspect the exact work-unit IDs and dependency edges when the observed order
differs from a simple topological level list.

## An executable is found but refused before launch

Agency ignores empty, dot, relative, and current-directory `PATH` entries and
rejects relative explicit commands. Configure an absolute executable path or
put the command in an absolute trusted `PATH` directory. Windows launchers must
resolve to an allowlisted native executable and cannot be links or reparse
points; a POSIX symlink is canonicalized to its real executable target.

`executable artifact changed before launch` means the canonical executable,
interpreter, or wrapper changed after preparation. This is a security failure,
not a transient success. Finish the package or host update, make sure the
artifact is outside the delegated target repository, and rerun from a fresh
preparation. Do not copy a replacement into the repository or relax discovery
to include the current directory.

`launcher-artifact-drift` or `launcher-artifact-unproven` refers to a
persistent generated host or dashboard launcher. The managed install manifest
binds the exact interpreter and Agency `_bootstrap.py` lexical/resolved
identity plus content digest. Do not edit that manifest or copy in a replacement
file. Finish the trusted package update, rerun `agency install` for host
adapters or `agency dashboard service install` for the dashboard, and inspect
status again before starting or restarting the service.

A current native bundle is only proof against the Agency distribution that
generated it; it does not prove that a same-version development checkout and an
older installed wheel contain identical runtime code. The release contract also
pairs a portable wheel with a distinct `win_amd64` wheel: compare the installed
filename, platform tag, package version, and exact recorded hashes, not version
alone. Neither profile may contain an Agency-owned executable or structurally
valid PE payload.

After building or reviewing a replacement wheel, install that exact artifact
into the interpreter recorded by `launcher_artifacts`, rerun
`agency install --agent <host>`, and require a fresh live canary before claiming
the host runtime is current. The canary must prove both the seven-field header and
correlated routing/finalization evidence; a zero host exit code alone is not
sufficient.

## WSL or Linux validation is missing tooling

Windows and WSL are separate Python environments. A Windows editable install
does not make `agency`, `pytest`, or dependencies available inside WSL. In the
Linux checkout/environment, create a venv and install the project before
claiming a Linux suite or live-host result:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest tests -q
agency eval routing --json --no-details
```

## Trace a failed runtime request

Browser, dashboard, HTTP, MCP, hook, and slow/error Store boundaries emit the
same metadata-only agency_observation envelope when INFO logging is enabled.
Use the request ID shown by the dashboard or returned in the
X-Agency-Request-ID header to correlate the fixed surface, operation, outcome,
reason code, duration, and optional Store generation. Request envelopes have
no field for prompts, tool arguments, bearer tokens, credentials, exception
messages, SQL text or values, or filesystem paths; correlation IDs are retained
only as one-way SHA-256 digests.

Agency Runtime does not create a new persistent observation-log database.
These envelopes go only to the process's configured standard logging sink and
therefore add no unbounded runtime-owned retention. If an operator routes that
sink into a file or log service, that external sink must have an explicit
finite rotation/retention policy. Durable SQLite evidence remains governed by
observability.retention_days and can be previewed and trimmed with the commands
below.

## SQLite is large or locked

Use a dry run before retention:

```bash
agency db stats
agency db trim --older-than-days 30 --dry-run
agency db trim --older-than-days 30
```

Runtime trimming preserves roster sources, candidates, snapshots, versions, and
active agents. Stop long-running processes if another process holds a write
transaction. Do not delete the database while host hooks or the dashboard are
running.
