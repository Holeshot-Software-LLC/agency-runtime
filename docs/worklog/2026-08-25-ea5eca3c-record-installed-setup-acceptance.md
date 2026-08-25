---
title: "Worklog detail: Record installed setup acceptance"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [setup, install, smoke, dashboard, evidence]
related:
  - docs/roadmap/issue-AR-289-native-reranker-transports.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-292-classify-setup-activation-pending.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: ea5eca3ced9d8ec766e267722f307409bd9a75ca
short: ea5eca3c
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-289-native-reranker-transports.md
  - docs/roadmap/issue-AR-292-classify-setup-activation-pending.md
---

# Worklog detail: Record installed setup acceptance

## Purpose

Record the exact installed-machine evidence that closes the bounded Jina
transport, smoke isolation, guided setup, and setup-degradation implementation
packages without conflating them with host activation or public release proof.

## Approach

Install the clean stacked worktree, hash-compare the affected source and
installed package files, run all-detected guided setup and deterministic smoke,
capture native exit codes explicitly across PowerShell's nonzero normalization,
and inspect configuration, doctor, dashboard service, host inventory, runtime
drift, and advisory pointer state. Preserve learned recall as typed-only because
no rotated private Jina credential is available.

## Challenges encountered

The first installed setup exposed alternate-home smoke pointers (AR-291); the
repaired repeat exposed setup's collapse of attended Codex activation into hard
failure (AR-292). After both fixes, PowerShell reported the degraded native exit
as shell status 1, so a final idempotent pass captured `$LASTEXITCODE` directly
and proved Agency returned 2. No live or paid model canary was run.

## Decisions and alternatives

The credential pasted in conversation was treated as exposed and was not put
in argv, YAML, logs, or a persistent environment. Empty learned routes retain
the byte-safe typed recall path. Native trust was not bypassed: Codex approval
and fresh Claude/ZCode loading remain owner/host actions, and doctor reports
them as degradation rather than claiming readiness.

## Verification

- Installed setup, installer, pointer isolation, native Jina reranker, and
  dashboard files matched the clean source SHA-256 hashes.
- Full installed setup registered Codex, Claude, and ZCode plus the per-user
  dashboard and passed all 8 deterministic smoke checks.
- The final idempotent setup pass captured native exit 2 with
  `installation: activation-pending`, no hard stage, and no runtime drift.
- Config validation and doctor returned degraded 2 only for host trust/load
  uncertainty; schema 48, 299 active agents, and both subscription providers
  passed.
- Dashboard inspection returned 0 and proved installed, owned, enabled, active,
  current, and reachable. Host status reported `runtime_drift: null`.
- Dense recall is `additive`, learned routes are empty, and `JINA_API_KEY` is
  absent from process and user environments.

## Follow-ups

The owner must restart the three installed harnesses, settle Codex hook trust,
and run the printed activation verification command before live host readiness
can be claimed. A rotated private key is required for an optional live Jina
route. Tracker, push, PR, hosted matrices, signing, tag, and release remain
separately unauthorized.
