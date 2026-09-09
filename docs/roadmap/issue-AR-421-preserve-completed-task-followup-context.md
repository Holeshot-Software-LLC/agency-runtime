---
title: "AR-421: Preserve completed-task follow-up context"
status: in_progress
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [reliability, native, staffing]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-421
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/808
depends_on: []
blocks: []
---

# AR-421: Preserve completed-task follow-up context

## Problem

The classifier drops available bounded same-session context for executable follow-ups after a completed task. Current go-for-it trace preserves the wrong new-intent classification and failed staffing.

## Current state

Phase live_demo. Version6 correlates completed-task replies/revisions
with fresh staffing; version1-5 receipts remain readable. Focused152pass;
seven new regressions fail against original version5, including real preflight
context handoff. Production spine1151pass/3skip, UI224pass, Ruff pass.
Native baseline review73.147s and multi-step114.055s complete with matching
accepted hashes; same-session "go for it"84.122s fails staffing. See
[evidence/AR-404-codex-suite-baseline-20260909.json](evidence/AR-404-codex-suite-baseline-20260909.json).
Verified artifactdb1c642f is installed; all614package files match and a fresh
isolated interpreter reports classifier6. Conformance188/188 passes. After-repair
native sample and isolated acceptance remain. Native refresh is now published as
1825059191a2/classifier6; Codex requires attended approval of8modified hooks.
The first post-wheel sample still ran classifier5 and the next had no Agency
receipt; neither is repair acceptance. Claude review now proves fresh classifier6
and accepted exact native evidence. Claude and Zcode follow-ups correlate the
exact completed review and require fresh staffing. Zcode additionally proves full
cards, all five headers and accepted hashes on both review and follow-up. Its
multi-step staffing failure remains in AR-404; isolated AR-421 verdicts are pending.

## Approach

Reproduce completed-task replies, route fresh with a correlated bounded subject, and retain every inference, critic, validator and source-state guard. No prior transcript or historical selection reuse.

## Dependencies

AR-404 retains the complete five-host reliability sample and all-host gates.

## Acceptance

- [ ] Reproduce the observed failure with exact, bounded evidence.
- [ ] Repair its cause while preserving trust, inference authority and unrelated work.
- [ ] Verify the repaired behavior with regression/native evidence and isolated verdicts.
