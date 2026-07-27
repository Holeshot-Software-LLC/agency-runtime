---
title: "AR-187: Isolate native host lifecycle commands from the caller CWD"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [security, host-integrations, processes, codex, installation]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/decisions/0106-isolate-native-host-lifecycle-working-directories.md
  - docs/THREAT_MODEL.md
  - CHANGELOG.md
  - agency_runtime/core/installer_native.py
  - agency_runtime/core/prepared_codex_install.py
  - agency_runtime/core/process_argv.py
  - tests/test_installer_coverage_complete_filesystem_native.py
  - tests/test_prepared_codex_install.py
  - tests/test_executable_discovery_security.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-187
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-187: Isolate native host lifecycle commands from the caller CWD

## Problem

The exact installed Codex refresh failed before mutation when invoked from the
user's home directory. `repository_forbidden_roots()` correctly treated its
supplied working directory as a recursive executable boundary, but the native
installer supplied the ambient caller CWD. A legitimate user-installed Codex
shim under `AppData/Roaming/npm` was therefore misclassified as repository
content because it is a descendant of the home directory.

Changing the shared boundary to trust arbitrary CWD descendants would reopen
AR-164: a repository could place a familiar executable in a sibling `bin`
directory. Native host lifecycle commands also inherited the ambient CWD even
though plugin inventory and registration are not repository operations.

## Current state

Native host lifecycle commands now prepare, freeze, and execute from an
owner-private ephemeral directory. They retain every marker-derived repository
ancestor from the ambient caller while omitting only the overly broad ordinary
CWD tree. The same private launch directory governs PATH sanitization and child
execution. The exact prepared Codex refresh uses the existing validated private
Agency runtime root for the full frozen transaction.

The live read-only Codex boundary resolves the npm installation to its native
vendor executable, freezes one persistent identity, proves `codex-cli 0.145.0`,
and runs from `C:\Users\lucas\.agency-runtime`. The state-changing exact-artifact
refresh and activation canary remain pending rebuild and installation.

## Approach

Keep the existing default recursive CWD boundary for delegation and repository
operations. Add a marker-only mode to inert repository discovery so
repository-independent lifecycle callers can combine the private launch tree
with every real ambient repository ancestor. Never consult Git to discover
those roots.

Thread the private launch directory through the least-privilege child
environment and the actual process CWD. Continue to resolve only absolute safe
PATH entries, reject every repository descendant lexically and canonically,
freeze every launcher artifact, validate owner-private directories, execute
without a shell, and revalidate immediately before spawn.

## Dependencies

AR-164 and ADR-0055 own repository-ancestor exclusion and executable identity.
ADR-0091 owns least-privilege environments. ADR-0104 owns the exact attended
Codex refresh. Tracker creation remains pending explicit outward-write
authorization.

## Acceptance

- [x] Invoking native Codex lifecycle work from a broad non-repository home no
  longer rejects a legitimate user-installed host CLI below that home.
- [x] Native children receive the same private working directory used for PATH
  preparation and executable freezing.
- [x] A nested repository still excludes its complete marker-derived ancestor,
  including sibling executable directories, after launch-CWD isolation.
- [x] The prepared Codex refresh uses a validated owner-private working
  directory and safe bare-command discovery for every frozen native call.
- [x] Focused native, prepared-refresh, and executable-discovery regressions
  pass warning-strict.
- [ ] The rebuilt exact artifact completes the attended Codex refresh and one
  fresh current-profile activation verification.

## Implementation evidence

The original installed artifact failed before commit with
`executable artifact must not reside in the target repository` for the npm
Codex shim. The focused corrected boundary passes 98 tests with one expected
platform skip. A real read-only prepared invocation from the same home resolves
the native Codex executable and proves its version without adapter, Store, or
trust mutation. The named production spine passes 522 tests with 5 expected
platform skips in 60.55 seconds; all 106 dashboard tests and the complete
routing/delegation evaluation gate also pass. No exhaustive or hosted workflow
ran.

Exact checkpoint `f3e8961e9029a89b956c03b18343f2d042cd24c6` produced a
strictly verified Windows wheel (SHA-256
`395488c8a96266927b7be2601c1aab92d9aba50ddc34f995052f5f98d83041fa`)
and source archive (SHA-256
`5993c6a60dff34b9dc60b86b86921caf5451f9cf7dd51a81f7ee88c0d49e329b`).
The uv tool receipt proves that exact wheel is installed and effective
delegation remains `prefer`. One attended refresh advanced past the original
executable-boundary failure and waited at native operator presence; without a
local approval it failed before commit after 132.4 seconds with state preserved
and no retry. AR-187 is therefore code-complete but remains operationally
`waiting_for_operator` for the acceptance item above.
