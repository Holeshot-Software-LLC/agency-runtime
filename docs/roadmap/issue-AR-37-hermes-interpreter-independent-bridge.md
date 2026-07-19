---
title: "AR-37: Make Hermes integration independent of the host Python environment"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [hermes, python, bridge, installer, portability]
related:
  - docs/decisions/0024-native-host-packages-and-minimal-bridges.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-37
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/38"
depends_on: []
blocks:
  - AR-43
---

# AR-37: Make Hermes integration independent of the host Python environment

## Problem

The generated Hermes plugin imports `agency_runtime` inside Hermes' interpreter,
while installation smoke imports it with Agency Runtime's interpreter. A pipx-
or virtualenv-separated Hermes install can register successfully and then fail
at runtime.

## Current state

Codex, Claude, and OpenClaw use an absolute Agency-owned interpreter or bridge.
Hermes is the exception and its deterministic smoke does not reproduce the
separated-interpreter boundary.

## Approach

Make the managed Hermes plugin a dependency-free standard-library adapter that
invokes a bounded JSON bridge through the absolute interpreter that installed
Agency Runtime. Keep shell disabled, argv explicit, input/output finite, errors
fail-closed, and runtime control available without importing Agency inside the
host environment.

## Dependencies

This applies ADR-0024's minimal host-bridge decision consistently to Hermes.

## Acceptance

- [x] Generated Hermes code does not import Agency Runtime in Hermes' interpreter.
- [x] Bridge argv, input, output, timeout, and failure behavior are bounded and shell-free.
- [x] Hooks and conversation controls preserve the authoritative correlation contract.
- [x] Separated-interpreter Windows/Linux install and hook regressions pass.
- [x] Full exact-coverage, package, and tracker gates pass.
