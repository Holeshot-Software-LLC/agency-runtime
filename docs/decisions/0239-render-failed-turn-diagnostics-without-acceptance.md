---
title: "Render failed-turn diagnostics without acceptance"
status: accepted
category: decisions
created: 2026-09-08
updated: 2026-09-08
tags: [headers, evidence, failure]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0239
type: decision
deciders: [owner]
---

# ADR-0239: Render failed-turn diagnostics without acceptance

## Context

A preflight_failed run is terminal but has an immutable failure receipt.
Requiring active state to display that receipt conflates failed staffing with
unreadable evidence. The owner requested repair of both staffing and headers.

## Decision

The header renderer may read the exact, validated failed-turn snapshot. It
reports recorded loaded/delegated/skill/model evidence and a failed recruitment
line containing bounded reason codes. The public finalizer returns these bytes
with action continue and preflight_failed true, never action accept. It performs
no terminal write. The normal completion gate still requires active state;
successful-turn replay, terminal rejection, and cross-session checks remain.

Persist the validated resident-manager binding on the same failed run when its
claim succeeds, in the same close transaction. Request-scoped hosts have no
persistent session binding to reconstruct later. Historical missing bindings
are not backfilled or inferred from today's controls.

## Consequences

Implementation ae2220bb and correlation follow-up992d148d are merged through
905d37b8/PR774; the worklog and reciprocal AR414 traceability retain these SHAs.

Operators can see what failed without a new staffing call or guessed headers.
This does not certify a native response, establish activation, or repair the
provider. Missing/corrupt evidence still cannot produce authoritative values.

## Alternatives

Reopening failed runs would erase their lifecycle meaning. Accepting arbitrary
terminal replies would weaken replay protection. Keeping all five values
unverified discards evidence the runtime already has. None is adopted.
