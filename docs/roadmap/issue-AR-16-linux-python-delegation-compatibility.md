---
title: "AR-16: Restore Linux and Python 3.12 delegation compatibility"
status: in_progress
category: roadmap
created: 2026-07-11
updated: 2026-07-12
tags: [linux, python, delegation, compatibility, testing]
related:
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0043-prime-stdin-before-windows-child-resume.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-16
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/16"
depends_on: []
blocks: [AR-07]
---

# AR-16: Restore Linux and Python 3.12 delegation compatibility

## Problem

The slotted dataclass transformations used for the Codex, Claude, and OpenClaw
backends can replace the class object after a zero-argument `super()` closure is
created. On Python 3.12 this caused structured response parsing to fail with
`super(type, obj): obj must be an instance or subtype of type`, even though the
same tests passed on newer Windows interpreters.

WSL can also inherit a Windows npm shim on `PATH`. Such a shim is discoverable
as `codex` but cannot necessarily execute with a native Linux `node`. An
optional current-machine capability check treated that unusable interop shim as
a product regression instead of reporting that the discovered CLI was not
usable in the current environment.

## Current state

Structured backends dispatch explicitly to the shared `CommandBackend` parser,
avoiding the dataclass/closure ambiguity across supported Python versions. The
optional installed-Codex capability check skips when a discovered executable
cannot run, while deterministic detection tests continue to distinguish
installed, authenticated, and usable states.

On Ubuntu 24.04 WSL with Python 3.12, the complete warning-strict suite ran from
a native ext4 copy and passed `2215` tests with `16` expected platform/host
skips. The separate performance selection passed both tests. This is local Linux
evidence. A fresh final-candidate wheel also installed cleanly under WSL/Python
3.12 and exercised packaged MCP discovery, authenticated dashboard health,
configuration defaults, assets, and every generated host bundle without
checkout-relative imports. The hosted Python 3.10 through 3.14 matrix remains
pending.

## Approach

Keep slotted dataclasses for their compact immutable configuration behavior, but
avoid zero-argument `super()` in methods added to those transformed subclasses.
Exercise the existing protocol tests on the complete Python 3.10 through 3.14
CI matrix and run the current branch from a native ext4 WSL copy. Treat PATH
discovery as evidence of presence only; execution capability remains a separate
fact.

## Dependencies

This is a cross-platform compatibility correction and blocks `AR-07` until the
native Linux suite passes.

## Acceptance

- [x] Codex, Claude, and OpenClaw structured response parsing does not depend on
  zero-argument `super()` in slotted dataclass subclasses.
- [x] Existing protocol success and failure cases pass on Python 3.12 Linux.
- [x] A discovered but non-executable WSL interop shim does not fail the
  optional current-machine capability test.
- [x] The complete Linux suite passes from a native ext4 working copy.
- [ ] Hosted CI passes the supported Python 3.10 through 3.14 Linux matrix.

## Verification

- `tests/test_delegation_backends.py` covers structured Codex, Claude, and
  OpenClaw success, terminal-state validation, redaction, and environment
  isolation.
- `tests/test_db_trim.py::test_cli_delegate_builds_noninteractive_backend_commands`
  covers the CLI-facing protocol boundary.
- `tests/test_host_canary.py::test_current_codex_cli_exposes_every_canary_command_capability`
  distinguishes a usable native CLI from a merely discoverable interop shim.
- Native Ubuntu 24.04 WSL on Python 3.12 passed `2215` tests with `16` expected
  platform/host skips from an isolated ext4 working copy. A separate run passed
  both performance tests.
- The final wheel installed into a clean WSL/Python 3.12 environment and passed
  MCP, dashboard-health, configuration, asset, and four-host bundle smoke.
- No Linux target host was installed for this run; it proves the Linux runtime,
  protocol, package, and host-contract suite, not live Linux host maturity.
- Hosted CI across Python 3.10 through 3.14 remains the sole unchecked
  acceptance criterion, so this item remains `in_progress`.
