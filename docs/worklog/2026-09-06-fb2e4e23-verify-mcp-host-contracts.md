---
title: "Verify current MCP host contracts against the legacy backlog"
status: active
category: worklog
created: 2026-09-06
updated: 2026-09-06
tags: [backlog, mcp, contracts, acceptance]
related:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
  - docs/roadmap/acceptance/issue-AR-131.md
  - docs/roadmap/acceptance/evidence/AR-131-current-contracts-20260906.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: fb2e4e2379939c7525018a14b2c54f8f15b168fb
short: fb2e4e23
date: 2026-09-06
pr: null
related_issues:
  - docs/roadmap/issue-AR-131-complete-mcp-cli-host-contracts.md
---

# Worklog: verify the current MCP host contract

## Purpose

Resume the owner-directed oldest-first loop after the explicit pause. AR-131
already has its original production schema fix, but lacks current acceptance.

## Approach

Trace schemas to the canonical host set, dispatch handlers, generated control
skills and bounded Store identifiers. Add ten targeted cases and strengthen
the host-enum assertion so a mismatched vocabulary cannot evade the check.
Freeze evidence for the six original criteria; their text is unchanged, with
unchecked task markers added because the isolated verifier requires them.
Update the canonical coordinator and capsule with resumed work and AR-135 next.

## Challenges encountered

The old public delegation tools were intentionally removed at eab8c085. Their
absence and fail-closed rejection are the current contract, not a reason to
restore them. Internal Store normalization still exists, so the evidence only
claims exact canonical boundary-sized identifiers, not arbitrary inputs.
The first docs check exposed the legacy Acceptance list lacking task markers;
adding unchecked markers preserves the original six statements.

## Decisions and alternatives

No product policy or production code changes. ADR-0117 governs owner authority
versus model-facing controls. The installed Codex skill matches the generator;
do not equate file identity with hook trust, live staffing or header correlation.
No repository-wide graph build: graphify orientation had no saved graph, so
use bounded source inspection. No specialist or native subagent was staffed.

## Verification

Current focused suite: 126 passed/five pre-existing skips (6.06s), up from 116
with the same skips before additions. Fresh named-spine baseline: 1075 passed/
three skips (67.21s); changed MCP file rerun in the focused package. UI: 138
passed. Routing gates pass. Ruff check/format pass for 764 files. Metadata,
policy, strict docs/tracker and diff checks pass. Detailed limits and commands
are in the linked evidence record. No new live or Windows proof is claimed.

## Follow-ups

Freeze candidate fb2e4e23 and run the isolated verifier. Do not flip done unless
all six original criteria are satisfied. Then publish/merge and continue to
AR-135, leaving Windows-specific work for the owner.
