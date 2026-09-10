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

AR-431 source05653bc9/artifactf95e0ab6 merged through PR840/841. The owner
confirmed trust; fresh inventory proves8/8 trusted candidate08689b5b8769 hooks.
The fixed initial native review passed on recipe22/classifier7 in78.818s:
session01a08b18-19fc-76f3-b5ea-4033b22c3291, trace01a08b18-1a43-7cb2-8b48-3d7f75b55d25,
four full cards, five Store-matching headers and authoritative finalization.
This proves the fresh-process initial gate, not the keep-going follow-up.
Delivery is live_demo; the exact same-session follow-up and isolated acceptance
remain pending. Prior failed receipts and the old parent's closed transport
remain separate. No all-host reliability claim.

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
