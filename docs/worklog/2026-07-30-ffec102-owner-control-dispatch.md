---
title: "Worklog detail: fix(authority): restore owner control dispatch"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [authority, cli, dashboard, automation, security]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: ffec1027ad18dee38469e710cd38049c00e3c9e2
short: ffec102
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: fix(authority): restore owner control dispatch

## Purpose

Make normal owner CLI and dashboard-service controls executable for both human
and autonomous owner workflows by removing the verifier that was intentionally
unavailable in production.

## Approach

Removed the shared pre-dispatch gate, its parser annotations, and the retired
module. Closed-world install and Codex-canary predicates now bind directly to
their public parser shapes. Prepared roster rollback uses the owner invocation
as authority while retaining exact primitive bindings and in-transaction Store,
generation, revision, activation-authority, and workforce revalidation. Model-
facing native controls remain read-only and now report that owner control is
required instead of implying a missing human-presence backend.

The obsolete AR-143 and AR-196 roadmaps were marked `wont_do` and superseded by
AR-204. Current threat, troubleshooting, release, handoff, CI, and test records
were reconciled without rewriting faithful historical worklogs.

## Challenges encountered

The presence contract was embedded beyond the main dispatcher: parser golden
manifests, install/canary shape sentinels, a permanently closed roster-rollback
stub, update-plan output, release hygiene, CI fast-spine paths, and active
recovery capsules all depended on it. Release verification also exposed a
pre-existing missing `test_decision_conformance.py` golden entry; the expected
workflow list now matches the workflow and repository instructions.

## Decisions and alternatives

ADR-0117 governs the authority change. Operation-specific confirmation,
compare-and-swap, immutable preparation, ownership, lock, rollback, and
postcondition checks were retained; only the unenforceable human distinction
was removed. Broker, hook, MCP, generated-host, and restricted brokerage paths
were not widened.

## Verification

- 708 focused tests passed with one platform skip across owner CLI, parser,
  install/uninstall, Codex activation shape, prepared transactions,
  dashboard-service recovery, host-control, security-turn, native installer,
  upgrade, and release contracts.
- Ruff passed all Python sources; 602 files were format-current.
- Metadata checked 559 Markdown documents; policy, worklog-currentness,
  documentation validation, and staged whitespace checks passed.
- Context telemetry reported 38.6 percent remaining, requiring this clean
  checkpoint before the next package.

## Follow-ups

Restore owner-only dashboard server dispatch and UI configuration/control
parity while proving broker requests remain read-only under AR-204.
