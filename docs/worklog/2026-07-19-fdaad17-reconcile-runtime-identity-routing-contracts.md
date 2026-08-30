---
title: "Reconcile runtime identity and routing contracts"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [documentation, configuration, routing, delegation]
related:
  - docs/roadmap/issue-AR-36-config-relative-runtime-paths.md
  - docs/roadmap/issue-AR-46-bind-routing-to-store-config-identity.md
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/roadmap/issue-AR-81-conflict-safe-direct-context.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: fdaad17
short: fdaad17
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-36-config-relative-runtime-paths.md
  - docs/roadmap/issue-AR-46-bind-routing-to-store-config-identity.md
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/roadmap/issue-AR-81-conflict-safe-direct-context.md
---

# Worklog detail: Reconcile runtime identity and routing contracts

## Purpose

Remove roadmap and README statements that described superseded behavior or
omitted user-visible path semantics after the implementation had changed.

## Approach

Document that relative database and policy environment overrides resolve from
the effective config directory. Update Store-bound routing status to describe
live omitted configuration and immutable explicit configuration. Reconcile
unit assignment with ADR-0068: unmatched units emit no worker suggestion and
resident managers never masquerade as domain workers. Describe the protected
manager pair as one compact resident-manager kernel under ADR-0065.

## Challenges encountered

The older unit-assignment record accurately described ADR-0054 at the time but
was later superseded by ADR-0068. Keeping the old coordinator-worker fallback
as current acceptance would have made correct present behavior look like a
regression.

## Decisions and alternatives

- Preserve stable issue identifiers and explain the superseding decision.
- Update maintained contracts, not faithful historical canary evidence.
- State environment override resolution explicitly rather than relying on
  tests or implementation details.
- Keep final hosted and merged-install gates visibly pending where they remain.

## Verification

- Documentation metadata and link validation passed for 226 Markdown files.
- The changed routing language matches current unmatched-unit and compact
  resident-manager regression tests.
- `git diff --check` passed.

## Follow-ups

Reconcile final gate checkboxes and current-state evidence after the exact
merged artifact is installed and the hosted matrix is green.
