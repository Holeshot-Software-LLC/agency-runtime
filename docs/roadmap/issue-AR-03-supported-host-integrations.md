---
title: "AR-03: Prove supported-host integrations"
status: done
category: roadmap
created: 2026-07-10
updated: 2026-07-12
tags: [adapters, installation]
related:
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-03
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/3"
depends_on: []
blocks: [AR-04, AR-07]
---

# AR-03: Prove supported-host integrations

## Problem

Writing a generated adapter file and importing it in a synthetic test does not prove that a real host discovers, loads, and invokes the integration. Unverified support claims can leave users with a successful installer message but no runtime behavior.

## Current state

The repository now generates a host-native bundle for each v1 target: a Hermes
plugin, an OpenClaw JavaScript package with a bounded Python JSON bridge, and
Codex/Claude marketplace plugins containing native hook and MCP manifests.
Deterministic tests cover installation, lifecycle commands, rollback, hook
translation, Windows command shims, and direct POSIX launch construction.

Support output separates `discovered`, `staged`, `registered`, `enabled`,
`loaded`, and `canary` facts. On the 2026-07-12 native-Windows inspection,
Codex 0.144.1 was discovered and the Agency Runtime plugin was registered and
enabled. Claude Code, Hermes, and OpenClaw were absent, so their generated
contracts were not relabeled as live host results.

The source checkout and an isolated Linux wheel install passed deterministic
routing, delegation, and generated-host smoke checks on Windows and WSL. Those
checks prove portable contracts, not native host discovery, loading, or
canaries. The later Codex result verifies only its explicitly reported Windows
isolated-profile scope; no real-profile host/operating-system pair is promoted
to `runtime-verified` by these results.

The packaged `agency host-canary` command now separates a nonmutating readiness
report from an exact-confirmed live attempt. Codex has a bounded isolated-profile
backend and Claude has an auth-only isolated-profile backend that explicitly
requests the managed plugin without using plugin-disabling `--safe-mode`;
Hermes and OpenClaw fail closed until an equally safe noninteractive mode is proven.
Successful evidence is nonce-bound, trace-correlated, content-free, and
fingerprinted to the OS, host version, managed install, bundle, and profile
scope. An isolated Codex attestation cannot promote real-profile maturity.

The generated Codex marketplace and plugin were accepted by the current
`codex-cli 0.144.1` validator. The installed `$agency status` skill loaded and
called the Agency status MCP tool, and the authenticated Codex CLI completed a
live keyless judge selection. Those results prove the skill/MCP and provider
paths, not host-hook execution or final evidence rendering.

A model-free `hooks/list` inspection found the expected three installed hooks
parser-clean and enabled but untrusted. Agency Runtime reports that real-profile
trust as `unverified` and does not read, mutate, or auto-trust Codex's live
trust store.

The exact-confirmed native Codex 0.144.1 canary then completed in its bounded
isolated profile with exit code `0`, `canary_passed=true`, a valid six-line
header with no missing fields, one nonce-bound routing event, one correlated
finalization, and a persisted attestation for trace
`019f5bdd-612d-70c0-b369-2b038faa3d02`. This proves the installed integration
can load, route, record evidence, and finalize a response through that bounded
isolated-profile host path. No model receipt was recorded. Its explicit
one-invocation trust bypass does not alter the real profile; an operator still
reviews the three hooks through `/hooks` and starts a new session before
expecting them there.

## Approach

Keep deterministic contract coverage and live maturity separate. Complete a
reproducible native canary for each operating-system/host combination that will
be called runtime-verified. Exercise discovery, installation, hook invocation,
routing context, evidence capture, finalization, disable, re-enable, and
rollback. Keep any target without that evidence below runtime-verified rather
than interpreting its generated bundle as a live result.

## Dependencies

None. The verified integration mechanisms established here are prerequisites for runtime controls and release claims.

## Acceptance

- [x] Each advertised host has a documented, truthful maturity state.
- [x] Every `verified` host discovers and invokes the installed integration in a realistic test or reproducible smoke procedure.
- [x] Install success in a verified scope means the target can actually use
      routing and evidence features; other scopes remain explicitly unverified.
- [x] Unsupported host names fail clearly, and stale roots are not auto-installed.
- [x] The support matrix, installer output, doctor checks, and tests use the same evidence-separated maturity model.

## Verification

- Codex 0.144.1 native inventory proved the managed plugin registered and
  enabled on Windows.
- The exact-confirmed isolated-profile canary exited `0`, produced a valid
  six-line header, recorded one routing event and one finalization, and persisted
  its nonce-bound attestation; it recorded no model receipt.
- The installed control skill called the Agency MCP status tool, the
  authenticated CLI completed a keyless judge selection, and isolated
  conversation controls exercised disable and enable while ending enabled.
- Real-profile hook trust remains deliberately manual and `unverified` until
  the operator reviews `/hooks`; isolated proof is not relabeled as durable
  real-profile trust.
- Claude Code, Hermes, and OpenClaw were absent from this machine and remain
  contract-covered rather than live-verified. Installer inventory never
  promotes an absent or contract-only host from generated files alone.
