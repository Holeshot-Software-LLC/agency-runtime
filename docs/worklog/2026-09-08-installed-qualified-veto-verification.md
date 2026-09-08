---
title: "Installed qualified-veto verification and self-contained regression"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [installation, critic, packaging, acceptance]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/roadmap/issue-AR-417-self-contained-qualified-veto-regression.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/roadmap/issue-AR-417-self-contained-qualified-veto-regression.md
---

# Installed qualified-veto verification and self-contained regression

## Purpose

The owner authorized building/installing the merged AR-416 repair, installed
captured-verdict replay, normal native evidence and isolated acceptance checks.
Clean synchronized baseline: b0dfd6310f478b6e26523f419ab875bcb6419e91.
Scope remains Linux/Codex; no publication, exhaustive matrix or Windows change.

## Approach

Use an owned worktree for edits and a separate clean clone for canonical builds.
The first builder invocation failed at the shared-worktree Git output bound;
a clean clone then rejected the cross-account-writable /tmp interpreter.
A trusted owner-private release environment passed unchanged builder guards.
Strict Twine and independent distribution verification passed for b0dfd631.
Portable wheel SHA256: e3df9ba61c3351e6d1db68cf4bd3e6313767baaf5098f4af2e67af0ba8829e0d.
Source archive SHA256: d52d03829f1b2be1c68888e3ff8a03078fda655840903ecb2e62f8bdd77d0dd0.
These preliminary artifacts were not installed into the live runtime.

## Challenges encountered

The verified source archive contains test_qualified_critic_reasons.py but omits
its referenced docs/roadmap/evidence/AR-414-native-critic-packet.json by existing
policy. The extracted regression failed one case with FileNotFoundError and
passed seven. AR-417 tracks this newly demonstrated packaging-test defect.
The corrected test pins the exact captured verdict, preserving its behavioral
assertions without widening archive policy or modifying runtime code.

## Decisions and alternatives

Reuse ADR-0074's governed payload policy. Widening that policy for a small
regression input is unnecessary. The full native packet remains repository
evidence; the test now carries the exact bounded verdict it exercises.

## Verification

Fresh focused checks before refinement: 124 passed. Fast production spine:
1151 passed, 3 skipped in72.68s. After the test-only refinement, focused124passed.
Targeted Ruff check/format pass. Rebuilt artifact, installed replay, native trust,
fresh native turn and isolated acceptance remain pending at this checkpoint.

## Follow-ups

Finish the verified rebuild and installation for AR-416; preserve any native
critic veto and stop at an actual operator-owned trust boundary if encountered.
Record isolated acceptance per criterion. AR-414/415/416/417 remain open until
their own evidence gates pass. No installed/native claim from source tests.
