---
title: "AR-30: Preserve noun phrases in delegation work-unit detection"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [delegation, routing, parser, testing, bug]
related:
  - docs/decisions/0019-bounded-machine-readable-cli-delegation.md
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-30
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/31"
depends_on: []
blocks: [AR-58]
---

# AR-30: Preserve noun phrases in delegation work-unit detection

## Problem

The imperative detector treated every verb-shaped token as a new work-unit
boundary. Words such as “design” and “review” can also be nouns, so a request
like “Review the authentication design, then document the deployment workflow”
was incorrectly split into three units instead of two. That distorted
delegation graphs and could change delegation recommendations.

## Current state

The full repository hardening suite reproduced the defect through the dashboard
routing lab. Existing tests covered lists, paths, sequential clauses, and exact
duplicate units, but did not cover a noun that is also present in the imperative
vocabulary.

## Approach

Keep the first imperative match permissive, then accept later verb-shaped
tokens as work-unit boundaries only when clause punctuation or an explicit
conjunction immediately introduces them. Preserve the bounded exact-duplicate
collapse and add selector-level plus dashboard-level regression coverage.

## Dependencies

This is a parser correction within the bounded delegation contract governed by
ADR-0019 and complements AR-27's authoritative delegation lifecycle work.

## Acceptance

- [x] Nouns such as “design” remain inside the preceding work unit.
- [x] Explicit sequential clauses such as “then document” remain separate units.
- [x] Exact duplicated work-unit text still collapses deterministically.
- [x] Selector and dashboard route-lab regressions pass.
- [x] Full repository validation and tracker synchronization pass.
