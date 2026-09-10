---
title: "AR-431: Preserve task context for keep-going recruitment"
status: done
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

Scoped acceptance complete against candidate2a3f7a5b; all three isolated criteria
satisfied. PR842 records native verification; source was merged in PR840.

Native session01a08b18-19fc-76f3-b5ea-4033b22c3291 passed the frozen initial
review in78.818s and exact keep-going follow-up in157.872s. Follow-up trace
01a08b1a-f50d-76d0-bb24-eb624109f97f is classifier7 continuation of completed
01a08b18-1a43-7cb2-8b48-3d7f75b55d25. Recipe22 applies bounded context and fresh
inference, with no cache/assignment replay. Four initial and five follow-up full
cards, all five Store headers and authoritative response hashes40bace52/5c36ceba
match exact native bytes. The follow-up retained an invalid reranker reply and
a primary recruiter timeout; configured content fallback succeeded, then the
independent critic accepted staffing. No caller retry, manual selection, bypass,
delegation or executed-test claim. PR842 carries these observations; isolated
acceptance satisfied all three criteria on the first isolated pass. No all-host reliability or historical-receipt repair.

Required source checks passed: focused163, additional critic5, production1151/3skip,
UI224, routing and conformance188/188; canonical artifact/smoke and exact installed
file checks passed. User trust is confirmed8/8 on candidate08689b5b8769.

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

- [x] Reproduce exact context loss and distinguish it from critic and transport outcomes.
- [x] Preserve bounded subject context for this phrase without weakening inference, critic or state guards.
- [x] Demonstrate fresh native recruitment, full selected cards, five Store-matching headers and authoritative finalization after focused and required fast checks.
