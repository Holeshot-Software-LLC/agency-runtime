---
title: "AR-03: Prove supported-host integrations"
status: in_progress
category: roadmap
created: 2026-07-10
updated: 2026-07-11
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
`loaded`, and `canary` facts. On the 2026-07-11 native-Windows inspection,
Codex was discovered but Agency Runtime was not registered; the other three
host executables were absent.

The source checkout and an isolated Linux wheel install passed deterministic
routing, delegation, and generated-host smoke checks on Windows and WSL. Those
checks prove portable contracts, not native host discovery, loading, or
canaries; no v1 host and operating-system pair is promoted to
`runtime-verified` by this run.

The packaged `agency host-canary` command now separates a nonmutating readiness
report from an exact-confirmed live attempt. Codex has a bounded isolated-profile
backend and Claude has an auth-only isolated-profile backend that explicitly
requests the managed plugin without using plugin-disabling `--safe-mode`;
Hermes and OpenClaw fail closed until an equally safe noninteractive mode is proven.
Successful evidence is nonce-bound, trace-correlated, content-free, and
fingerprinted to the OS, host version, managed install, bundle, and profile
scope. An isolated Codex attestation cannot promote real-profile maturity.

The generated Codex marketplace and plugin were accepted by the current
`codex-cli 0.144.1` validator and isolated plugin inventory. That is a
manifest/lifecycle capability check, not a model invocation or a live hook
canary. No real model-backed host canary was run, so the live acceptance
criteria remain open.

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
- [ ] Every `verified` host discovers and invokes the installed integration in a realistic test or reproducible smoke procedure.
- [ ] Install success means the target host can actually use routing and evidence features.
- [x] Unsupported host names fail clearly, and stale roots are not auto-installed.
- [x] The support matrix, installer output, doctor checks, and tests use the same evidence-separated maturity model.
