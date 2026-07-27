---
title: "Worklog detail: attended Codex refresh proof"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [production-readiness, codex, dogfood, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: worklog
commit: 85428e6345c63677547ba0eaf6c778d8ad50d3d8
short: 85428e6
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
---

# Worklog detail: attended Codex refresh proof

## Purpose

Preserve exact local artifact, Windows Hello, installation, registration, and
remaining-activation evidence before the current-profile live canary.

## Approach

Built the committed source from a clean detached worktree with an owner-private
Python runtime, verified the wheel and sdist independently, installed the wheel
into a fresh private venv, and inspected the real existing Codex host before
mutation. Retained the first safe pre-mutation verification failure, then used a
taskbar-visible process for the attended Windows Hello success. Recorded only
bounded non-secret artifact, install, backup, bundle, version, and policy
identities from read-only post-install status.

## Challenges encountered

The canonical builder correctly rejected both the primary checkout's unrelated
untracked draft and the repository venv's cross-account-mutable ACL. A clean
worktree and fresh owner-private build environment satisfied those boundaries.
The first hidden UI attempt timed out before mutation; the visible retry passed.

## Decisions and alternatives

No hook-trust bypass, direct marketplace rewrite, native inventory edit, or
reuse of the failed verification result was allowed. Registration remains
separate from activation under ADR-0104.

## Verification

- Strict Twine and independent distribution verification passed.
- Fresh wheel version and real Codex status smoke passed.
- The first attempt reported no partial state and no recovery requirement.
- The visible attended transaction exited zero.
- Read-only status proved the new install, bundle, retained backup, exact native
  version, enabled state, source paths, and policies.

## Follow-ups

Run a fresh-process current-profile Codex canary. Preserve a failure as failure;
do not infer loaded hooks from installation or registration.
