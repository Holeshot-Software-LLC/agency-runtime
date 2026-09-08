---
title: "AR-409 installed live delivery checkpoint"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [installation, live-evidence]
related:
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/roadmap/acceptance/evidence/AR-409-installed-live-delivery-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: ba9cd8690d239d4ad161d6e3c76c4754b14dda60
short: ba9cd869
date: 2026-09-07
pr: null
related_issues: [docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md]
---

# AR-409 installed live delivery checkpoint

## Purpose

Record exact-main artifact and owner installation before fresh native tests.

## Approach

Build the accepted merge independently, compare every installed package payload
file, refresh four existing owner hosts and retain source/projection identities.

## Challenges encountered

Native activation is distinct from installation. Claude executable namespace
permissions recurred; exact restrictive repair does not establish its actor.

## Decisions and alternatives

Apply existing owner install/activation policy and ADR-0235 without changing
budgets, profiles or credentials. Preserve separately sourced OpenClaw and the
running dashboard instead of silently changing their authority.

## Verification

Artifact build/portable/Twine, isolated installed CLI/MCP/dashboard, eight
generated smoke checks, 613-file installed comparison and four installers pass.
Metadata/docs/diff gates pass. Native checks remain pending.

## Follow-ups

Complete scoped native evidence and publish this delivery branch by the owner
cutoff. AR-409 remains open until the installed live checkpoint is reconciled.

Installed checkpoint `ba9cd869` records exact main `4db6be16` before native provider calls. Source PR #739 is already merged; this delivery record awaits its own PR.

Native checkpoint `a005076c` records all current host outcomes and exact fingerprint attribution: no current all-host pass. Codex trust and provider failures remain visible; separate AR-410 targets wasteful warm-up staffing. No acceptance judgments were changed.
