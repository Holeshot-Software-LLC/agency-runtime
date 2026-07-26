---
title: "AR-136: Persist native-child correlation and fail planned work closed"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [routing, delegation, hooks, evidence, security]
related:
  - docs/THREAT_MODEL.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/delegation/native_labels.py
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-136
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-136: Persist native-child correlation and fail planned work closed

## Problem

Codex and Claude parent-child correlation lives in a HookBridge dictionary,
but each installed hook event runs in a fresh process. Planned-shaped native
delegations also pass through unchanged when Store or correlation resolution
fails, allowing side effects before evidence is enforced.

A parseable native activation marker is additionally trusted before Store
verification. Because the envelope is encoded and hash-consistent but not
authenticated, a forged marker on a canonical planned label can skip the
PreTool denial and reach side effects before PostTool evidence fails.

## Current state

Same-instance tests forward parent session, trace, worker, and run IDs. A new
bridge instance forwards none. Store failures for valid planned labels return
an empty pass-through response for Claude, Codex, and ZCode.

## Approach

Persist a bounded, expiring, single-consumer parent-scope receipt keyed by
host-native child identity and exact parent evidence. Resolve it atomically in
the later hook process. Recognize Agency-planned labels before lookup and deny
on missing, ambiguous, stale, or unavailable evidence; leave generic unplanned
host delegations pass-through.

## Dependencies

ADR-0094 defines receipt authority and fail-closed behavior.

## Acceptance

- Two real hook subprocesses preserve the exact parent scope once.
- Replay, ambiguity, timeout, wrong host, and wrong child identity fail closed.
- A planned-shaped label plus Store failure cannot start side effects.
- Generic non-Agency delegations remain pass-through.
- Parent budgets, cache, singleflight, activation, and terminal lineage use the
  same durable scope.
- A forged but parseable delivery never bypasses pending-grant verification.
- Codex and Claude use an explicit durable child receipt because their
  documented UserPromptSubmit payload cannot be guessed into an automatic
  child-session join.
- ZCode claims only planned PreTool/PostTool lineage until the host exposes a
  real child lifecycle identifier.

## Implementation evidence

Schema 37 persists bounded hashed native-child scopes with exact host, parent,
child, expiry, and single-consumer controls. A failed prepared preflight is
restored for retry, expired scopes can be reissued, ambiguity fails closed, and
planned work cannot pass through on Store or correlation failure. Separate
parent and child hook subprocess regressions prove one exact consumption,
replay denial, forged-delivery rejection, and generic-unplanned pass-through.
The integrated native-hook/ZCode slice passed 167 tests.
