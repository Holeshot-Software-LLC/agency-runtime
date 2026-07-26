---
title: "Worklog detail: Harden production readiness wave one"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [production-readiness, security, mcp, sqlite, hiring, release]
related:
  - docs/analysis/2026-07-26-production-readiness-review.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 24948a0
short: 24948a0
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-128-seal-model-facing-control-authority.md
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/issue-AR-130-revalidate-store-trust.md
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/issue-AR-132-hire-deterministic-safe-gaps.md
  - docs/roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-136-persist-native-child-correlation.md
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
---

# Worklog detail: Harden production readiness wave one

## Purpose

Correct the first independently reproduced production blockers without
weakening security, schema, staffing, or release gates, and preserve an exact
hard checkpoint for the remaining autonomous work.

## Approach

Removed model-facing MCP and restricted-broker mutation authority, aligned MCP
schemas with canonical Store bounds, isolated installer/delegation child
environments, removed stale positive Store-trust caching, added schema 36
currentness and retention invariants, repaired deterministic multi-gap hiring,
and trimmed redundant dashboard bytes below the unchanged asset ceiling.

The checkpoint also records two later audit results instead of hiding them:
forged native activation markers can bypass planned-work PreTool enforcement,
and the model-callable Browser can automate owner-dashboard mutations. AR-136
and the new AR-143/ADR-0096 keep those P0 gates open.

## Challenges encountered

The first combined suite exposed four stale generated-skill tests even though
isolated MCP suites were green. Exact adjacent bundle/smoke tests were updated
and the combined suite rerun. Schema currentness initially detected missing
objects but not same-name weakened SQL; canonical trigger/index definitions and
adversarial altered-object tests closed that gap.

## Decisions and alternatives

ADR-0091 and ADR-0092 govern least-privilege child environments and
non-cacheable positive filesystem trust. ADR-0096 supersedes ADR-0090's
owner-dashboard exception because a bearer and typed modal inside a
model-controlled browser do not prove operator presence.

## Verification

- Combined Python checkpoint: 785 passed, 9 skipped.
- Dashboard Node interaction suite: 97 passed.
- Schema 36 fresh/upgrade/tamper/retention suite: 11 passed.
- Release packaging: 15 passed; assets 263,151 of 263,168 bytes.
- Ruff check and format check passed across 543 files.
- Documentation validation passed for 367 maintained Markdown files.
- `git diff --check` passed.

## Follow-ups

Implement AR-143, AR-133, AR-135, and AR-136 next; then complete dashboard
truth/observability, performance, compatibility, fresh installation, installed
dogfood, AR-125, and the full release checklist. Tracker creation, push/PR,
hosted checks, normal-profile Codex trust, and publication remain explicit
authorization or user-presence boundaries.
