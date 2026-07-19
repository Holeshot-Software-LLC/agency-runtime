---
title: Gate roster activation through quarantine and approval
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-16
tags: [roster, governance, security]
related:
  - docs/roadmap/issue-AR-02-specialist-coverage-gaps.md
  - docs/roadmap/issue-AR-28-reversible-agent-activation-controls.md
  - docs/roadmap/issue-AR-102-refresh-legacy-bundled-roster-contracts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0013
type: decision
deciders: []
---

# ADR-0013: Gate roster activation through quarantine and approval

## Context

Roster sources can change independently of the runtime. Activating downloaded specialist definitions immediately would let an upstream change alter routing and prompt behavior without review.

## Decision

Process roster updates through registered source, download, normalization, quarantine, snapshot diff, approval, activation, and audit stages. Manual approval is the default.

Allow automatic approval only for sources explicitly marked trusted. Automatic sync fails closed if any enabled source is untrusted, any source fails to fetch or validate, or the current sync yields no valid quarantined candidates. Scope approval to candidates from the current sync. Seeding bundled starter entries must not overwrite an already activated synced specialist.

## Consequences

- Roster changes are reviewable before they affect routing.
- Trusted automation is possible without making all sources trusted.
- Partial source failure cannot silently activate an incomplete roster.
- The store must retain source trust, snapshots, candidate status, and activation history.

## Alternatives

- Activate every fetched source immediately. Rejected because it makes external change an implicit code path.
- Disable automation entirely. Rejected because explicitly trusted sources need a safe unattended mode.
- Merge starter entries over active entries on every install. Rejected because installation must not downgrade approved roster content.

## Provenance

Commit 8b377b1 documented the quarantine-to-activation governance model. Commit 3b24614 added source trust, fail-closed automatic approval, current-sync scoping, pruning behavior, and non-destructive starter seeding.
