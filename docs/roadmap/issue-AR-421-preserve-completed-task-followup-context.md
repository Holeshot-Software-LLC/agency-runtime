---
title: "AR-421: Preserve completed-task follow-up context"
status: done
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

Done for completed-task subject correlation. Classifier6 (cf4ed77f) preserves
the bounded source of a completed task for contextual replies/revisions while
requiring fresh staffing and execution decisions. Failed/untrusted state, new
explicit work, independent critic and validators retain their guards.

Focused152 tests and selector/context43 tests pass; the original classifier
negative control is7failed/12passed. The installed artifact is db1c642f, native
projection1825059191a2. Fresh Claude and Zcode follow-ups point to their exact
completed reviews; Zcode also proves full cards, all five headers and accepted
response hashes. Evidence is retained in the fixed AR-404 suite.

All three current isolated criteria are satisfied. The first criterion3 absent
verdict is retained in AR-421-first-isolated-verdicts-20260909.json; its circular
requirement for existing isolated verdicts was separated from the observable
behavior check. Mandatory isolated verification still governs closure.

This does not establish all-host reliability. Codex needs native hook trust,
Hermes/OpenClaw still time out, Claude has AR-423 delivery limits, and Zcode's
multi-step staffing failed. Those remain under AR-404.

## Approach

Reproduce completed-task replies, route fresh with a correlated bounded subject, and retain every inference, critic, validator and source-state guard. No prior transcript or historical selection reuse.

## Dependencies

AR-404 retains the complete five-host reliability sample and all-host gates.

## Acceptance

The repository-mandated isolated verdicts gate closure after these observable
criteria are judged; a criterion does not require its own verdict to pre-exist.

- [x] Reproduce the observed failure with exact, bounded evidence.
- [x] Repair its cause while preserving trust, inference authority and unrelated work.
- [x] Verify the repaired behavior with regression and fresh native evidence.
