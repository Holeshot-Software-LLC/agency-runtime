---
title: "AR-115: Make live routing and Agency headers trustworthy"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [routing, headers, delegation, dashboard, testing]
related:
  - README.md
  - agency_runtime/core/header/explanations.py
  - agency_runtime/core/selector/judge.py
  - agency_runtime/server/mcp_tools.py
  - docs/decisions/0078-present-human-routing-evidence-and-abstain-on-noise.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-115
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/127
depends_on: []
blocks: [AR-116]
---

# AR-115: Make live routing and Agency headers trustworthy

## Problem

A verified Codex turn exposed raw routing codes in the user-facing header,
selected unrelated geography and clinical specialists for a runtime/dashboard
question, and rejected delegation preparation when Codex described its native
worker more specifically than Agency's durable generic-worker attribution.
Passing synthetic evaluation scores did not catch this real prompt.

## Current state

The installed dashboard is active and reachable, but the response header is
written for machines rather than people. When optional local inference is not
available, very weak deterministic embedding collisions can still become
specialist selections. The MCP delegation boundary forwards native worker
labels into a store contract that intentionally accepts only generic-worker.

## Approach

Keep raw reason and effect codes in the signed durable receipt and render a
deterministic plain-English projection in the six-line response header. Require
a minimum signal before heuristic fallback may select a specialist; otherwise
abstain and let the resident orchestrator and chief of staff handle the turn.
Normalize supported native-host worker labels to generic-worker at the MCP
boundary while continuing to reject arbitrary specialist-like attribution.
Add the observed prompt and explicit forbidden specialists to regression and
live verification coverage.

## Dependencies

ADR-0001 defines layered routing, ADR-0011 defines delegation evidence,
ADR-0027 makes correlated receipts authoritative, and ADR-0030 requires
quantitative routing gates.

## Acceptance

- [x] User-facing Why and How lines are readable prose.
- [x] Raw reason and effect codes remain in durable routing receipts.
- [x] Weak heuristic collisions abstain instead of selecting unrelated specialists.
- [x] Supported Codex native worker labels normalize to generic-worker attribution.
- [ ] The observed prompt is verified against the installed runtime with forbidden-specialist checks.
- [ ] Dashboard and public documentation explain the live test workflow.
- [ ] Full repository, hosted CI, merge, reinstall, and Codex smoke gates pass.
