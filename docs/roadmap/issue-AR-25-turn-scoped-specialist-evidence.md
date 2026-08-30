---
title: "AR-25: Scope specialist evidence to the current turn"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-18
tags: [evidence, tracing, finalization, hooks, reliability]
related:
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0007-six-line-evidence-header.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-25
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/26"
depends_on: []
blocks:
  - AR-26
  - AR-27
  - AR-33
  - AR-79
  - AR-81
  - AR-85
---

# AR-25: Scope specialist evidence to the current turn

## Problem

Loaded-specialist evidence is stored and validated as a cumulative session set.
Long-running sessions therefore require stale agents in later response headers,
even when those agents did not shape the current turn. The public finalization
tool also accepts missing correlation and can manufacture an apparently valid
`loaded: none` header from an empty evidence lookup.

## Current state

Every active specialist, skill, delegation, model, and finalization claim is
bound to an explicit session and trace. Public finalization rejects missing,
partial, non-ready, terminal, or mismatched correlation. Terminal close and
evidence mutation are mutually exclusive, active specialist projection expires
with the turn, and historical session evidence remains immutable in a separate
bounded dashboard view. Legacy session-only rows migrate as history and cannot
be promoted into a current header.

## Approach

Retain immutable session history while recording every activation against a
required trace and session. Make current-turn specialist, skill, delegation,
model, finalization, and Stop queries use the trace. Require explicit correlation
at public mutation boundaries, expire active semantics at the end of the turn,
and keep bounded prompt injection separate from historical reporting. Expose the
historical activation projection separately to the dashboard. Migrate existing
stores without promoting legacy session-only rows into current-turn evidence.
Persist a privacy-safe request fingerprint and typed state-aware turn
classification on the turn parent so separate hook processes can enforce the
same contract. Retain trivial/nontrivial only as a legacy projection for older
completion boundaries; ADR-0064 owns the authoritative classification.
Make evidence writes and terminal closure mutually exclusive transactions, keep
terminal outcomes monotonic, and close failed preflights instead of leaving an
ambiguous active trace.

## Dependencies

This correction supersedes ADR-0016's session-wide evidence association and
applies ADR-0027's requirement that visible runtime claims come from correlated
events. It is coordinated with AR-26 and AR-27 but can be verified independently.

## Acceptance

- [x] Specialist activation records carry both session and trace identities.
- [x] Session history remains queryable without becoming current-turn evidence.
- [x] Headers and Stop verification use only the current trace's specialists.
- [x] Prior-turn skills, delegations, and model receipts cannot leak into a header.
- [x] `agency.finalize` fails closed when correlation is missing or incomplete.
- [x] Main-agent prompt injection has an explicit count and character budget.
- [x] Legacy databases migrate without data loss or false current-turn claims.
- [x] The dashboard exposes bounded historical activations separately from current state.
- [x] Typed turn classification and its legacy enforcement projection survive adapter restarts and separate hook processes.
- [x] Evidence writes cannot race terminal closure or duplicate one activation.
- [x] Failed preflight is terminal and cannot contaminate later trace recovery.
- [x] Expired-preflight recovery atomically removes every trace evidence record
      and rejects stale-owner ready/fail updates.
- [x] Public mutations reject evidence-only, in-progress, and otherwise
      non-ready preflight correlation.
- [x] Repeated diagnostic route/explain calls create no open evidence lifecycle.
- [x] Focused, full, coverage, documentation, and tracker validation pass.
