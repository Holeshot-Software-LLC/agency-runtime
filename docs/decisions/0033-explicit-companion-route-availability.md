---
title: "Classify every companion route against explicit availability"
status: accepted
category: decisions
created: 2026-07-11
updated: 2026-07-16
tags: [routing, policy, roster, governance]
related:
  - docs/roadmap/issue-AR-02-specialist-coverage-gaps.md
  - docs/roadmap/issue-AR-26-bundle-default-coordinators.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0033
type: decision
deciders: []
---

# ADR-0033: Classify every companion route against explicit availability

## Context

The companion policy names a much broader set of specialists than the bundled
starter roster. A syntactically valid route can therefore point at a slug that
does not exist in the active governed roster. Treating every configured slug as
available would produce confident but unusable routing advice; silently
dropping missing slugs would hide policy drift.

The policy also contains both action routes and division anchors. Validating
only one surface leaves the other able to accumulate unresolved specialists.

## Decision

Maintain one explicit availability classification for every unique specialist
slug referenced by either an action route or a division anchor. A route is
either `bundled`, meaning the starter roster must provide an active governed
specialist, or `roster_gated`, meaning it stays disabled until an approved
active roster supplies that slug. Every roster-gated entry carries a stable
reason.

Generate the availability block deterministically from the policy and check it
in CI. Validation fails when a referenced slug is unclassified, a bundled slug
is absent or inactive, a roster-gated entry has no reason, or an availability
entry is no longer referenced. Runtime resolution skips unavailable routes and
reports the reason rather than presenting them as usable companions.

## Consequences

- The broad policy can remain expressive without overstating starter-roster
  coverage.
- Adding or removing a route creates a reviewable generated-policy change.
- Approved roster activation can make a gated route eligible without changing
  routing code.
- Required bundled specialists become an installation and validation
  invariant.
- The generated registry is intentionally large, but its mechanical nature is
  preferable to implicit availability spread across code paths.

## Alternatives

- Bundle every referenced specialist. Rejected because it would bypass roster
  governance and turn a focused starter set into an unreviewed catalog.
- Delete routes that are not currently bundled. Rejected because it discards
  useful governed policy and makes future activation harder to audit.
- Ignore missing slugs at runtime. Rejected because silent degradation cannot
  distinguish deliberate gating from policy drift.
- Validate only action routes. Rejected because division anchors influence the
  same selection system and require the same truth boundary.

## Provenance

AR-02 records the implementation and verification. Its implementation commit
is linked through the roadmap and worklog after the final validated change is
committed.
