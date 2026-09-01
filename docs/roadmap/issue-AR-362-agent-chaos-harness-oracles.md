---
title: "AR-362: Add an agent-chaos harness with explicit failure oracles"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [chaos, testing, battery, reproducibility]
related:
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-352-scope-battery-deltas-by-session.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-362
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/435
depends_on: []
blocks: []
---

# AR-362: Add an agent-chaos harness with explicit failure oracles

## Problem

Our reliability evidence is observational: batteries watch turns and
wait for failures to occur naturally. Intermittent defects therefore
have no repro — the AR-353 staffing window can only be measured by
waiting for it to flap, and the AR-297 review's runner hard-kill
recovery gap has never been exercised deliberately. A defect we cannot
inject is a defect we cannot regression-test.

## Current state

No injection machinery exists. Provider outages, hard kills, and
timing windows are reproduced by luck or not at all.

## Approach

Build a small chaos layer (concept lifted from LobeHub's achaos
packages, owner-approved 2026-09-01) with portable contracts:

- **Experiment**: a named scenario (provider timeout during staffing,
  runner hard-kill mid-run, gateway restart mid-turn).
- **Effect**: the injected fault, applied through owned adapters only
  (hook delivery, provider client, process ownership-checked kills).
- **Safety**: bounds that keep experiments off live user turns —
  dedicated sessions, rollback on exit.
- **Oracle**: the explicit pass/fail judgment (e.g. "run closes
  preflight_failed with a receipt and the next turn fails open with
  Rule-8 pass-through").
- **Receipt**: a stored result row so chaos runs are evidence.

Start with the two named scenarios above; wire results into the
battery report.

## Dependencies

- Pairs with AR-360 (trial semantics) for grading repeated experiments.

## Acceptance

- [ ] The AR-353 staffing-window shape is injectable on demand and its
      oracle passes against the shipped fail-open behavior.
- [ ] A runner hard-kill experiment exists and its recovery oracle
      records the current behavior (pass or documented gap).
- [ ] Experiments run only in dedicated sessions with rollback, never
      against live user turns, enforced in code.
