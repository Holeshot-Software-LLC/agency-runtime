---
title: "AR-194 service-runtime inspection reconciliation"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, dashboard, launcher, portability, windows]
related:
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/decisions/0050-isolate-installed-python-module-resolution.md
  - agency_runtime/core/launcher_bootstrap.py
  - agency_runtime/core/dashboard_service_core.py
  - agency_runtime/core/dashboard_service_inspection.py
  - tests/test_launcher_bootstrap.py
supersedes: []
superseded_by: null
---

# AR-194 bounded source and installed-status evidence

This is a builder receipt, not an acceptance verdict. Source is
`f408b6f2325ca86bc058364d0f688acff1dac45a`. The original July Windows
CPython-3.10/3.13 mismatch is historical; it was not reproduced on a Windows
machine tonight. No service installation, restart, repair, owner package
change, model inference or native Windows call was performed for this package.

## Original acceptance, unchanged

- [x] Read-only verification accepts a well-formed owned runtime pinned to a
  different supported Python cache tag.
- [x] Preparation and execution still reject a foreign, malformed, mismatched,
  or unproven interpreter/tag/runtime combination.
- [x] Dashboard service status reports the real state of a valid cross-version
  owned runtime instead of an invalid-manifest error.
- [x] Focused launcher and dashboard-service tests pass with strict hash, path,
  manifest, and namespace validation retained.
- [ ] An attended owner-side service repair replaces the stale task/runtime and
  a current installed status check reports the new worker reachable.

## Criterion and authority map

| Criterion | Current evidence and exact scope |
|---|---|
| 1 | `launcher_bootstrap.py:762-781` verifies an existing immutable projection with `expected_python_cache_tag=None`; `:344-388` still requires a canonical bounded tag and hash-named canonical manifest. `tests/test_launcher_bootstrap.py:188-217` accepts a self-consistent synthetic `cpython-999` tag and rejects malformed tags. This is format/identity proof, not execution support for Python 999. |
| 2 | `launcher_bootstrap.py:503,625,662,676,696` keep exact current-tag preparation boundaries. `dashboard_service_core.py:503-565` probes the selected identity-bound interpreter with fixed `-I -S -c`, no shell, bounded output, timeout and pre/post identity revalidation before preparation. `tests/test_dashboard_service_coverage_complete_core.py:575-711` covers exact/current native probe and foreign, malformed, oversized, nonzero, timeout and drift refusals. |
| 3 | `dashboard_service_core.py:585-618` reads the manifest's exact seven-element worker argv and uses inspection-only projection verification. `dashboard_service_inspection.py:565-667` separately reports ownership, registration, manifest currency, visibility and reachability. `tests/test_launcher_bootstrap.py:220-292` uses a synthetic foreign-tag Windows-shaped fixture with a mocked manager reporting absent: owned manifest, stale registration, repair recommended, no manifest error. It does not invoke PowerShell. Actual Linux status is retained below. |
| 4 | Fresh 116-test selection below; all supplied fixtures retain existing validation. No production or test changes were needed. The 42 name-filtered cases are deselected, not passed. Some retained tests model Windows interfaces under mocks; no native Windows result is claimed. |
| 5 | NOT demonstrated: no stale Windows task/runtime was repaired, and no post-repair Windows reachability was measured. Actual Linux health below does not prove this historical transition. ADR-0117 removes the separate human-presence ceremony only; exact owner authority, ownership, transaction and postconditions remain. |

ADR-0040 preserves lexical environment-owned interpreter paths; ADR-0050
requires isolated fixed bootstrap dispatch. Both remain accepted. ADR-0109's
old service-presence design is superseded; AR-196 is `wont_do`, superseded by
AR-204. ADR-0117's Decision expressly admits normal owner CLI and autonomous
owner-directed service controls without a second OS ceremony. Therefore the
canonical dependency on implementing AR-196 is removed, not its meaningful
platform evidence. No new architectural policy is introduced here.

## Fresh focused command and raw stdout

Working directory was this branch worktree; the explicit test interpreter is
the already-existing private verification environment. No real host service
is installed or mutated by these fixture tests.

```text
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_launcher_bootstrap.py tests/test_dashboard_service_coverage_complete_core.py tests/test_dashboard_service.py -q -W error -k 'not windows'
........................................................................ [ 62%]
............................................                             [100%]
116 passed, 42 deselected in 2.75s
```

Exit 0. The foreign-tag regression already exercises inspection versus
preparation without executing the foreign fixture interpreter. The real
current-interpreter probe executes only fixed cache-tag inspection, not a
provider or service process. No broad corpus or native Windows suite was run.

## Installed owner status, before any later owner upgrade

Executed from `/tmp`, outside the checkout, at approximately
2026-09-08T00:12Z (September 7 Eastern). Exact command:

```text
agency dashboard service status --json
```

Exit 0; command-tool elapsed 0.202215105 seconds. Below is the complete JSON
with only the owner-home path prefix replaced by `<owner-home>` for portability.
No bearer or configuration values were read into this receipt.

```json
{
  "action": "inspect",
  "active": true,
  "definition_drift": false,
  "enabled": true,
  "exit_code": 0,
  "installed": true,
  "manager": "systemd-user",
  "manager_available": true,
  "manager_environment_durable": true,
  "manifest_current": true,
  "manifest_owned": true,
  "manifest_path": "<owner-home>/.agency-runtime/services/dashboard-service.json",
  "non_durable_manager_environment_overrides": [],
  "ok": true,
  "owned": true,
  "platform": "linux",
  "reachable": true,
  "registration": "agency-runtime-dashboard.service",
  "registration_owned": true,
  "registration_path": "<owner-home>/.config/systemd/user/agency-runtime-dashboard.service",
  "repair_recommended": false,
  "stale_manifest": false,
  "supported": true,
  "visibility_limited": false,
  "worker_argv": [
    "/usr/bin/python3",
    "-I",
    "-S",
    "<owner-home>/.agency-runtime/launchers/runtime-sha256-4329d76058d18eaa6b02f0b5750ff5533462064028c1178a8b5e913364774fac/site-packages/agency_runtime/_bootstrap.py",
    "agency_runtime.server.dashboard_service",
    "--config",
    "<owner-home>/.agency-runtime/agency.yaml"
  ]
}
```

`cli/service_commands.py:167-195` dispatches `status` only to
`inspect_dashboard_service(..., _validate_launcher=True)`. This is distinct
from `open`, whose owner-authorized recovery may mutate. Inspection reads the
existing projection; it does not prepare or publish a launcher. No `open`,
install, start, restart, stop or uninstall command was run.

## Source identity and limits

The installed `agency` shebang identifies the existing
`ar348-20260905.qq1DjJ` Python environment, not the worktree interpreter.
`sha256sum` on the following worktree files and their installed
`lib/python3.12/site-packages/agency_runtime/` counterparts returned these
identical pairs:

| Package-relative file | SHA-256, identical source and installed |
|---|---|
| `core/launcher_bootstrap.py` | `887437e026bbaf73b01afeebd10eb24889321c887a903690cf6efd5e705e1684` |
| `core/dashboard_service_core.py` | `e92f3c3d30f30ed1f61fb983679ccbb647fbc2bf3f88d52ed7ba7bbf66eec80c` |
| `core/dashboard_service_inspection.py` | `a06a8f846a193e31283b351f2ac5872d0c16413b22c548e6f8e6c86749d8fb97` |
| `cli/service_commands.py` | `11728143a5a04dc8844158f8d29126e1c43742002a0327d735c1af593a41bcfc` |

This binds the inspected four-module slice only. It is not a claim that every
installed module equals `f408b6f2`, that the live worker uses all current-main
code, or that an actual cross-Python service migration occurred tonight.
Reachable/current status establishes the existing Linux worker's reported
health at that read, not model staffing, dashboard control mutation, Windows
Scheduled Task health, or future status after another package upgrade.

## Remaining bounded work

Before the checkpoint: metadata checked 1,252 Markdown files; policy
availability and worklog checks passed; `verify_docs.py --require-tracker`
passed 1,252 files; strict `verify_tracker.py` passed 400 roadmap items with
two historical PR-tracked exclusions. Repository Ruff lint passed and format
reported 769 files already formatted. `git diff --check` passed. A direct
`diff` against source `f408b6f2` proved the complete five-criterion checkbox
block byte-identical. These checks do not judge acceptance.

Retain AR-194 `in_progress` with the original Windows transition visible. On
the owner's Windows machine, collect exact current CLI/runtime identities,
read-only status and an owner-authorized stale-to-current repair with its
post-repair reachability. Do not reinstall a healthy Linux service merely to
manufacture that transition. Prepare acceptance only when the meaningful
platform clause has evidence or a separately justified owner decision changes
the scope; this receipt performs neither action.
