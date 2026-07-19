---
title: "AR-26: Bundle the no-match coordinator fallback"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-18
tags: [routing, fallback, roster, installation, reliability]
related:
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/decisions/0033-explicit-companion-route-availability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-26
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/27"
depends_on: [AR-25]
blocks: [AR-81]
---

# AR-26: Bundle the no-match coordinator fallback

## Problem

The configured no-match policy names `agents-orchestrator` and
`chief-of-staff`, but both are roster-gated and absent from the starter roster.
A clean installation therefore abstains without loading the fallback that the
policy and user-facing enforcement expect to exist.

## Current state

Tests can activate the two agents manually, masking the fresh-install gap. The
generated availability registry classifies both as gated, while starter seeding
provides neither prompt. Header enforcement can consequently demand a specialist
after routing had no usable default candidate.

## Approach

Ship governed, versioned starter prompts for both coordinators and classify them
as bundled. Apply them as the deterministic fallback only when routing produces
no substantive match, including trivial no-signal turns. Preserve normal
specialist selection when a confident action route exists, enforce the global
prompt budget, and verify fresh-store behavior across every host surface.
Idempotently repair upgraded nonempty rosters that predate the bundled pair.
Pre-read the active slugs so an unchanged preflight performs no serialized
activation transaction, while the inner insert remains race-safe if a prompt is
actually missing.

## Dependencies

This changes the availability data governed by ADR-0033 without weakening its
validation boundary. AR-25 supplies the turn-scoped activation semantics used
when the fallback is injected.

## Acceptance

- [x] Fresh starter stores contain active governed prompts for both coordinators.
- [x] Upgraded nonempty stores repair either missing protected coordinator.
- [x] Availability classifies both fallback agents as bundled.
- [x] Genuine no-match and trivial no-signal turns select both agents.
- [x] Confident specialist matches do not receive the no-match fallback.
- [x] Routing explain output identifies the deterministic fallback source.
- [x] An unchanged preflight performs no fallback-activation write transaction.
- [x] Host, install, routing-evaluation, and full validation pass.
