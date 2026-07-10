---
title: "AR-03: Prove supported-host integrations"
status: open
category: roadmap
created: 2026-07-10
updated: 2026-07-10
tags: [adapters, installation]
related:
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
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

The repository contains dedicated runtime wiring for Hermes and a native JavaScript package plus Python bridge for OpenClaw. Codex and Claude currently receive a generic Python hook scaffold at host-specific paths. Tests prove adapter parity and generated-file imports, but they do not prove that those two hosts discover or support that hook contract. The public support matrix currently presents all four as wired.

## Approach

Define a support maturity matrix with `verified`, `experimental`, and `planned` states. For every verified host, test installation, discovery, hook invocation, routing context, evidence capture, finalization, disable, and re-enable against a realistic host harness. Where a host does not support the generated hook form, replace it with an officially supported wrapper, server, configuration, or command integration; otherwise mark it unsupported without writing inert files.

## Dependencies

None. The verified integration mechanisms established here are prerequisites for runtime controls and release claims.

## Acceptance

- [ ] Each advertised host has a documented, truthful maturity state.
- [ ] Every `verified` host discovers and invokes the installed integration in a realistic test or reproducible smoke procedure.
- [ ] Install success means the target host can actually use routing and evidence features.
- [ ] Unsupported hosts fail clearly and do not receive inert scaffolding.
- [ ] The support matrix, installer output, doctor checks, and tests agree.
