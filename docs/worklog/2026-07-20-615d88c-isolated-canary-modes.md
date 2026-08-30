---
title: "Bind isolated canaries to explicit global modes"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [canary, runtime-control, codex, claude, testing]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/roadmap/issue-AR-88-compare-agency-native-outcomes.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 615d88c88af4a62f1bbbdfdbcc0050cb7426b19c
short: 615d88c
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114
related_issues:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/roadmap/issue-AR-88-compare-agency-native-outcomes.md
---

# Worklog detail: Bind isolated canaries to explicit global modes

## Purpose

Correct an isolated-profile defect that reset the durable Agency-wide master
switch to its default enabled state. The defect made a requested Agency-off
comparison execute and record Agency-on evidence.

## Approach

Add explicit `agency` and `native-only` canary modes with distinct exact
confirmation phrases. Read the real authoritative master-control document,
require it to match the requested mode, materialize the same enabled value in
the private temporary home, and verify the real document did not change during
the observation.

Keep Agency mode's existing header, correlation, identity, and attestation
contract. Give native-only mode the inverse evidence contract: successful
nonempty response, registered or explicitly requested isolated plugin, no valid
Agency header, zero new runtime evidence, and no Agency attestation.

## Challenges encountered

The defect was visible only in a real isolated Codex profile because the SQLite
evidence path was already shared while the master-control path was implicitly
derived from the replaced home. The complete Windows suite later passed 6,903
tests and skipped 35 but reported two timing-only failures under aggregate load.
An isolated routing report passed every accuracy and performance gate; a repeat
microbenchmark landed 0.001 ms above the strict 2 ms cache p95 boundary, so no
green aggregate performance claim is made from that run.

## Decisions and alternatives

[ADR-0076](../decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md)
records why a durable control projection and evidence exclusion are required.
An environment-only override and plugin uninstall were rejected because neither
exercises the installed master-control boundary being compared.

## Verification

- Focused canary/CLI contract suite: 100 passed.
- Added negative coverage for mode mismatch, empty output, unexpected Agency
  headers/evidence, control read failures, control drift, and projection failure.
- Ruff check and format gates passed across package, tests, and scripts.
- Metadata and documentation link validation passed for 245 Markdown files.
- Full Windows suite: 6,903 passed, 35 skipped, two timing-only failures.
- Isolated routing report: every routing, policy, delegation, determinism, and
  performance gate passed; cache-hit p95 was 1.664 ms.

## Follow-ups

Build and install the exact commit artifact, run paired Agency-on/native-only
Codex canaries with guaranteed restoration, and complete the hosted matrix under
[AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md).
