---
title: "Enforce actual hiring provider independence"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [hiring, security, configuration, regression]
related:
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/decisions/0221-enforce-hiring-independence-on-resolved-provider-chains.md
  - docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c9b678a57bf3626b816cfe368de74001292ec0da
short: c9b678a5
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/687
related_issues:
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
---

# Worklog detail: fix(hiring): enforce independence across resolved provider chains [AR-348]

## Purpose

Honor the owner's explicit strict-independence policy, which previously did
nothing in hiring. The red checkpoint 2e5454bc contains 20 failing strict cases
and 23 passing controls. Keep the actual outcome separate from the ticket's
incomplete global-profile-only proposed fix.

## Approach

The existing enforcer accepts resolved chains from the production resolver.
Initial critic/security pairs are checked before the first creator call and
again at review invocation. Safety repair binds its own creator chain before
replacement and review. Shared fallback entries also fail; no provider is
selected, replaced, filtered or reordered. The warning and strict checks share
one adapter/model comparison. Default false behavior and inference authority
remain unchanged.

## Challenges encountered

The first guard implementation reported only the first entirely-legacy
conflict, leaving one of 43 tests red. Aggregating initial pairs in the existing
helper reports both exact routes. Extracting that bounded preflight also keeps
the existing hiring function under its unchanged complexity limit. No test
assertion or lint threshold was weakened. An attempted python -m invocation
failed because this package has no __main__; its real CLI entry point then
passed routing.

## Decisions and alternatives

ADR-0221 records actual-chain enforcement and the limits of configured identity.
The old config-load wording was not implemented; effective harness resolution
belongs at hiring time. Do not claim provider-company or physical-backend
independence behind opaque aliases. The original two acceptance criteria stay.

## Verification

413 focused passes/one existing skip; named spine 1075 passes/three existing
skips; UI 138 with unchanged production coverage floors; routing and Ruff pass.
Two new curated mutations bring the catalog to 184; 17 catalog tests pass.
Protected mutation execution, isolated acceptance and installed smoke remain
pending at this commit, not inherited from the preceding package's receipts.

## Follow-ups

Finish this AR-348 acceptance/delivery package, then AR-349's separately tracked
rejected-hire persistence. Windows, provider configuration and attended host
trust remain outside this fix.
