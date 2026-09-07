---
title: "Scope Route Lab duplicate ambiguity to the affected host identity"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, hosts, eligibility, availability]
related:
  - docs/roadmap/issue-AR-151-align-route-lab-host-eligibility.md
  - docs/roadmap/acceptance/evidence/AR-151-host-eligibility-20260907.md
  - docs/decisions/0095-complete-paginated-dashboard-collections.md
  - agency_runtime/server/dashboard.py
  - agency_runtime/dashboard/dashboard-render.js
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0225
type: decision
deciders: [maintainers]
---

# ADR-0225: Scope Route Lab ambiguity to host identity

## Context

AR-151's original first criterion says, verbatim: "Duplicate and oversized host
inventories cannot enable Route Lab." Its isolated review at f954d1e9 correctly
contradicts that blanket wording: both current UI and server allow an unrelated
unique verified host when a different host appears twice. The implementation
record at 6a3bdaa and direct 13-case contract at 58285009 establish this shared
per-host behavior; current full-dashboard evidence is at 99e05d1f.

The owner asked backlog review to judge relevance and contradictions rather
than treat every historical agent-written proposal as current product intent.
The underlying defect is authorizing an ambiguous host, not permitting a
different host whose identity, enablement and receipt are unambiguous.

## Decision

Exclude every occurrence of a duplicated canonical execution-host identity
from Route Lab eligibility. Never choose a first or last duplicate as authority.
An unrelated unique host remains selectable only with its own valid current
native installation receipt and effective enablement. Keep POST authoritative.

Reject an inventory exceeding the existing ten-row bound in its entirety,
because the bounded completeness assumption no longer holds. Count unknown
rows toward that bound. Render explicit bounded ambiguity/size reasons.

Replace only AR-151's blanket first criterion with this explicit contract:
"Duplicate host identities cannot authorize Route Lab, oversized inventories
disable it entirely, and unrelated unique verified hosts remain selectable."
Preserve the original wording and contradicted verdict in history. The other
three criteria remain unchanged and all four require new isolated verdicts.
This records current product behavior, not an accepted old-criterion result.

## Consequences

- Ambiguity cannot authorize the affected host or poison an unrelated verified
  host's availability. More than ten rows still blocks the entire operation.
- Client and server retain the same host-specific authority and no runtime
  code changes are required for this decision.
- AR-151's first requirement is explicitly revised, not silently marked passed.

## Alternatives

- Block all hosts whenever any duplicate appears: rejected because it would
  add an unrelated availability restriction without stronger selected-host proof.
- Keep the first or last duplicate: rejected because order is not authority.
- Drop unknown rows before counting: rejected because it evades the inventory bound.
