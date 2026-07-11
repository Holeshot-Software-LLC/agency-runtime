---
title: "Troubleshooting Agency Runtime"
status: active
category: operations
created: 2026-07-10
updated: 2026-07-11
tags: [operations, troubleshooting]
related:
  - README.md
  - SECURITY.md
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
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
```

Do not interpret a generated file as a loaded integration. The host inventory
must advance through discovery, registration, enablement, loading, and canary
evidence separately.

## Host was not discovered

`agency install --all` selects a host only when its executable is on `PATH` or a
current native-state marker exists. A bare `~/.codex`, `~/.claude`, `~/.hermes`,
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

## OpenClaw refuses installation

The installer will not restart a live OpenClaw gateway. If the result says
`host_restart_consent_required`, schedule a maintenance window, stop the gateway
with the host's native procedure, rerun the installer, and restart it yourself.
Then use native inventory and runtime inspection to establish loaded/canary
state.

## Registered but runtime unverified

`registered-enablement-unverified` and `enabled-runtime-unverified` are honest
cold-inventory states, not failures hidden behind success language. Restart the
host when required, exercise a harmless preflight, and inspect again. Only a
native runtime surface can promote `loaded` or `canary`; file existence cannot.

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

## Dashboard service does not install or start

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

## No specialist is selected

Zero-signal input intentionally abstains. For a meaningful task, inspect the
active roster and decision receipt:

```bash
agency roster list
agency policy --json
agency explain "describe the concrete task" --session-id debug
```

If the roster is empty, run `agency install` to seed missing starter agents or
activate an approved roster snapshot. If a provider fails, the decision receipt
shows fallback; deterministic routing remains available.

## Delegation remains suggested or skipped

A suggestion is not proof that a host delegated. Confirm the host called a
recognized delegation tool and that its result indicates success. Failures,
timeouts, malformed structured output, unavailable executables, and failed
prerequisites remain `skipped` or `failed`. Check the work-unit identity in the
evidence view or SQLite record rather than matching only the agent name.

The generic backend is unavailable until configured with an explicit command.
That is intentional; it never turns a no-op into completed work.

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
