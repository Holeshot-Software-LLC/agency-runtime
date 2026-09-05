---
title: "AR-401: Enforce preflight deadlines at provider boundaries"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, staffing, reliability]
related:
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/roadmap/issue-AR-398-a-gap-turn-that-outruns-its-lease-leaves-no-receipt.md
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-401
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/666
depends_on: []
blocks: []
---

# AR-401: Enforce preflight deadlines at provider boundaries

## Problem

The round-admission estimate allows sequential creator, critic and security calls to overrun the preflight lease. Planning, repairs, provider fallback and recall can spend the same lease without sharing its absolute deadline.

## Current state

The independent 2026-09-05 review reproduced the defect at main `e6531004`.
The owner requested implementation, PR merge, installation and smoke testing of
all harnesses. Package phase: demo_ready. Focused regressions and the named fast
spine pass (1004 passed, three skipped); 182 curated conformance mutations are
killed. Implementation checkpoints are `47ab9fce`, `e9d8ecea` and `af366dd8`.
Installed/live host outcomes remain due; AR-403 separately records live recall timing.

## Approach

Bind one absolute inference deadline to preflight routing, reserve terminal-recording time, clamp each provider call to its remaining budget, and refuse any subsequent call after exhaustion with a named receipt. Keep direct calls without a preflight deadline compatible.

## Dependencies

Delivered with AR-400, AR-401 and AR-402 as one bounded staffing-correctness package.
Existing native host trust and gateway credentials remain operator-owned.

## Acceptance

- [ ] Real hiring stages and fallback calls share an absolute deadline; a simulated 75-second lease cannot start a third 50-second call, and refused work leaves a named hiring account.
- [ ] Planning, semantic repair, structured recall, embeddings and native reranking honor the same routing deadline without leaking it to another request.
- [ ] Deadline exhaustion through preflight leaves a terminal failure receipt and never commits incomplete pending workers.
