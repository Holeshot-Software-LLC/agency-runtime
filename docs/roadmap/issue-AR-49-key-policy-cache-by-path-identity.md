---
title: "AR-49: Key companion policy cache by requested path identity"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-15
tags: [routing, policy, cache, configuration, correctness]
related:
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-49
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/50
depends_on:
  - AR-46
blocks: []
---

# AR-49: Key companion policy cache by requested path identity

## Problem

The companion-policy cache fast path can return a previously loaded custom
payload after the caller switches to a different missing or default policy path.
For the recheck interval, one config identity can route with another identity's
policy.

## Current state

Policy reloads use path and modification state, but the short recheck fast path
can run before requested identity is compared and reset. Tests observed the
stale custom payload during no-match routing.

## Approach

Include canonical requested path identity in every cache fast-path decision and
clear stale payload/metadata before fallback when identity changes. Preserve the
bounded recheck optimization only for the same exact request key.

## Dependencies

AR-46 binds routing to one config snapshot. This item makes ADR-0021 policy
caching honor that identity throughout the turn recipe.

## Acceptance

- [x] Switching policy paths can never return the prior path's payload.
- [x] Missing/default fallback is immediate even inside the recheck interval.
- [x] Same-path unchanged calls retain the bounded fast path.
- [x] Concurrent route/explain calls remain deterministic.
- [x] Full exact-coverage, Windows/Linux, performance, and tracker gates pass.
