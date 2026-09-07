---
title: "AR-164 current repository-ancestor executable boundary evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [security, executables, evidence, acceptance]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/acceptance/issue-AR-164.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/roadmap/acceptance/evidence/AR-163-remediation-authority-20260907.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-164 current executable-boundary evidence

## Scope and current source

Reviewed after PR #714 merged 6d1ca01fb572e58bc5b1186bc9114ae0b7a789ba;
clean merge ledger 7e0dc5d9b064d51123f98127fa5dc716f9d65972. Original ancestor
repair f64ba1e and lifecycle-CWD correction 63a1f5f2 remain present. No runtime,
script or test change was needed. One stale acceptance component mapping is
explicitly reconciled under ADR-0227 before isolated review.

Current process_argv discovers all repository ancestors by inert marker lstat,
without a Git or hook call. Unreadable markers fail conservatively. Shared
discovery filters sibling repository directories; explicit paths and resolver
results face final lexical/resolved-root checks, and freezing checks every
launch-critical artifact. Revalidation remains immediately before execution.
A legitimate absolute directory outside these roots remains eligible.

AR-187's lifecycle isolation uses a private launch CWD while retaining actual
ambient repository ancestors. It does not recursively exclude an ordinary
non-repository home or permit a repository sibling bin.

## Fresh focused verification

Python 3.12.3, Linux, checkout-local imports:

```bash
PYTHONPATH=. python -m pytest tests/test_executable_discovery_security.py \
  -q -W error -k 'not windows_approved_powershell_companion_identity_is_frozen'
```

**38 passed, one native-Windows-only deselection, 0.14s**, no skips/failures.
Includes actual Linux directory/symlink fixtures, first Git selection through
its production preparation path (process runner captured, not a live Git
invocation), explicit/resolver rejection, replacement identity and safe external
PATH cases. Windows spelling/drive/case/PATHEXT cases run as portable simulations,
not native Windows execution.

```bash
PYTHONPATH=. python -m pytest tests/test_cli_transport_coverage_complete.py \
  tests/test_dashboard_service_coverage_complete_core.py \
  tests/test_smoke_isolation.py tests/test_smoke_coverage_complete.py \
  tests/test_installer_coverage_complete_filesystem_native.py \
  tests/test_delegation_process_lifecycle.py -q -W error -k 'not windows'
```

**129 passed, 23 Windows-named deselections, 3.39s**, no skips/failures.
Current six-module launch package includes marker-error handling, private native
CWD with ambient repository exclusion, service-manager preparation and existing
isolated generated-host smoke contracts. It is not attended native installation.

```bash
PYTHONPATH=. python -m pytest tests/test_git_runner.py tests/test_bounded_process.py \
  tests/test_delegation_git_security.py -q -W error -k 'not windows'
```

**24 passed, three Windows-named deselections, 0.63s**, no skips/failures.
This verifies the surviving extracted Git/bounded-process subjects, not the
deleted delegation classes. No new skip or xfail was added to the suite.

## Retired and current surfaces

Actual Git inspection of fb34191f9380cdeab2895878e5a933c2cda35608 shows removal of
backend_command.py, backend_hosts.py, lifecycle_dispatch.py, orchestration and
worker ledger. git_runner.py and bounded-process helpers survive. The current
checkout has no CodexExecBackend/CommandBackend registration or worker dispatcher
in those deleted modules. AR-236's August 12 checkpoint records the merged Job B
decision; North Star R5 preserves native-host ownership.

Current CLI-provider calls prepare/freeze through cli_transport._resolve_cli;
native installer calls preserve marker roots through private launch-CWD
preparation; dashboard_service_core._run and smoke's Node syntax preparation use
the same shared roots at discovery and freezing. ADR-0227 changes only criterion
5's component mapping and preserves the old sentence. No retired execution API
was revived.

## Exact-byte broader receipts and limits

```bash
git diff --exit-code fcdcd6eb -- agency_runtime tests scripts AGENTS.md pyproject.toml
git diff --exit-code fd551fd4 -- agency_runtime/dashboard tests/dashboard_ui.test.mjs
```

Both return zero. Reuse AR-162's named warning-strict spine (1085 passes,
three existing skips, 68.09s) and AR-163's whole DOM result (188 passes,
197.292186 ms). No redundant run is implied. Existing same-byte AR-156
loaded-browser evidence is broader context, not a new browser launch.

No exhaustive corpus/coverage/matrix, hosted dispatch, native Windows,
PowerShell, ACL certification or host-activation canary. AR-129/130/147 and
AR-187 retain their own native/attended obligations. AR-164 is an exempt legacy
record, not a reason to create or close an unrelated tracker. No candidate-bound
verdict is assigned by this receipt.

## Publication validation

Fresh metadata and strict documentation checks pass for 1180 Markdown files;
tracker parity passes 397 mapped items with two historical PR exceptions.
Policy availability and the exact 1974-commit worklog check pass. Ruff check
and format pass for 766 files. Scoped git diff --check returns zero. These
are local publication checks, not hosted CI or native Windows qualification.
