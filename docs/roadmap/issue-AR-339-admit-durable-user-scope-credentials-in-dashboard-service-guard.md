---
title: "AR-339: Admit reboot-durable user-scope credentials in the dashboard service guard"
status: open
category: roadmap
created: 2026-08-31
updated: 2026-08-31
tags: [dashboard, windows, service, credentials, reliability]
related:
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/handoffs/issue-AR-338.md
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-339
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/372
depends_on: []
blocks: [AR-338]
---

# AR-339: Admit reboot-durable user-scope credentials in the dashboard service guard

## Problem

The dashboard service worker refuses to start whenever any config-declared
credential environment name is present in its process environment
(`run_dashboard` raises `dashboard_service_environment_error`). On Windows a
Task Scheduler worker always inherits the user-registry environment — the
sanctioned location for secrets under the per-harness posture recorded in
AR-338's owner interview — so on a machine whose configuration declares
`api_key_env` credentials the fresh-runtime dashboard can never become
ready. `agency install --all` starts the fresh worker, the worker exits at
the guard, the readiness probe times out, and rollback restores the previous
task definition with the report "dashboard service did not become ready with
a fresh runtime".

## Current state

Measured 2026-08-31 during the AR-338 Windows bring-up: the fresh worker
(runtime `c4815c3a...`) run in the foreground exits with a RuntimeError at
`server/dashboard.py:3164` naming `JINA_API_KEY` (declared by the Jina
recall profiles). The 2026-08-25 runtime (`b60cbe5d...`) predates the
`configured_credential_environment_names` collection and its worker runs
under the identical environment; that older worker was restored and serves
on 127.0.0.1:7810 meanwhile. Receipt:
`~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`
(`defects_found.dashboard_service_env_guard`). The Linux container flow
never hits the guard because its secrets live in the LiteLLM proxy and the
systemd user-manager environment is clean.

## Resolution (2026-08-31, worker fix landed; registered refresh pending)

`dashboard_service_environment_overrides` now admits a config-declared
credential whose process value is byte-equal to its registry-persisted
Windows user-scope (or machine-scope) value; a process-local-only or
mismatched value still fails closed, the static `AGENCY_*` runtime
overrides stay flagged regardless of persistence, and no value ever leaves
the in-process equality check. Live on the AR-338 Windows machine: the
fixed worker was started in the foreground under the exact environment
that made the pre-fix worker raise instantly (`JINA_API_KEY` inherited
from the user scope) and it served `HTTP 200` on `127.0.0.1:7810` with
zero stderr. The old-runtime scheduled task was restored afterwards; the
remaining acceptance box is the registered-service refresh through
`agency install --all`, which waits for the next anchored install so the
AR-338 host projections keep their exact-main provenance. Receipt:
`~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`
(`fixes_verified_20260831.ar339_dashboard_env_guard`).

## Approach

Keep the guard's intent — a reboot-durable service must not depend on
process-local-only secrets — while admitting the durable case. On nt, treat
a process value that is byte-equal to the HKCU user-scope persisted value as
reboot-durable, or scrub configured credential names from the worker
environment at service start instead of refusing. Never read, print, or
persist the values themselves; the comparison and the scrub are names-only
plus an equality check performed in process.

## Dependencies

None. The fix is confined to the dashboard service environment guard and
its Windows durability semantics.

## Acceptance

- [x] On Windows, with a config-declared credential persisted in the HKCU
      user environment, the fresh dashboard service worker starts and the
      readiness probe passes.
- [x] A credential present only process-locally (absent from the durable
      scope) still fails closed with the existing names-only diagnostic.
- [x] No credential value is copied into the service definition, manifest,
      task XML, diagnostics, or logs.
- [ ] AR-338's `agency install --all` acceptance reaches "dashboard
      healthy" on the Windows machine.
