---
title: "AR-431: Preserve task context for keep-going recruitment"
status: in_progress
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [codex, recruitment, reliability]
related:
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - docs/decisions/0163-resolve-contextual-turns-from-transcript-free-subjects.md
  - docs/worklog/2026-09-10-codex-recruitment-context.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-431
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/839
depends_on: []
blocks: []
---

# AR-431: Preserve task context for keep-going recruitment

## Problem

Codex reply `keep going` was classified as new intent and lost its completed
predecessor's bounded task subject before fresh staffing. The recruiter repaired
an invalid response, then the independent critic vetoed the repaired team.

## Current state

Implementing a bounded classifier repair. Exact failed trace
`01a088e1-a95b-7190-b0fb-760284a0c92c` and reconstructed prior state are retained in
`evidence/AR-431-original-context-loss-20260910.json`. The reconstruction exactly
matches the recorded state hash. Classifier6 drops context for `keep going`;
`go ahead` retains it against the same state. The original raw model packets
are unavailable, so the critic veto is not declared erroneous or attributed
solely to context loss. Separate finalization returned Transport closed and
remains unconfirmed. No old receipt is reopened.

Classifier7 recognizes the exact phrase; recipe/context22 separates current
classification from historical projections. Negative control3 failed/27 passed;
repaired focused163 passed. Required fast checks, canonical artifact, installed
file/trust inspection, fresh native follow-up and isolated acceptance are pending.
The current parent runs stale projection6db15efbecbe versus published37c1bf7d5eb0;
reinstallation alone cannot refresh that process. Zcode work remains deferred.

## Approach

Extend the existing bounded continuation phrase set. Completed task replies
carry their guarded transcript-free subject to fresh inference, with no replay
of completed assignments. Missing, stale, ambiguous, corrupt and failed state,
explicit new requests, critic and validator authority retain their boundaries.
This implements ADR-0064/0163 rather than adding staffing authority.

## Dependencies

AR-404 retains broader host reliability. Native Codex hooks require normal host
trust and a fresh process; no bypass or manual acceptance is permitted.

## Acceptance

- [ ] Reproduce exact context loss and distinguish it from critic and transport outcomes.
- [ ] Preserve bounded subject context for this phrase without weakening inference, critic or state guards.
- [ ] Demonstrate fresh native recruitment, full selected cards, five Store-matching headers and authoritative finalization after focused and required fast checks.
