---
title: "AR-186: Bound delivery to live demo checkpoints"
status: done
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [governance, delivery, testing, demo, cost]
related:
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - AGENTS.md
  - CONTRIBUTING.md
  - docs/RELEASE_CHECKLIST.md
  - docs/NORTH_STAR_ACCEPTANCE.md
supersedes: []
superseded_by: null
type: issue
epic: documentation-governance
issue_id: AR-186
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-186: Bound delivery to live demo checkpoints

## Problem

Production-readiness work expanded into an open-ended cycle of reviewing every
surface, fixing every discovered item, and trying to certify every historical
gate before showing one installed behavior. That cycle consumed excessive time,
tokens, and hosted-test budget while obscuring whether the product worked.
Repository policy also made one expensive broad workflow mandatory for
production and release, and implied that a task should continue through
human-owned transitions instead of exposing a waiting state.

## Current state

The named fast spine, focused regressions, artifact verifier, installed smoke,
and live host/UI evidence are independently available. Exhaustive coverage and
compatibility remain useful diagnostics but are already excluded from ordinary
pull requests and pushes. Human trust, signing, publication, and external
settings remain explicitly operator-owned.

## Approach

Make each delivery package start with one observable outcome and move through a
small explicit sequence: scope, implement, focused review, fast verification,
exact build/install, live demo, done. Fix only findings that block that outcome;
record unrelated findings for later. Use at most two independent review passes
unless unresolved Critical/High evidence or an owner request justifies more.

Treat exhaustive CI as optional, explicitly requested diagnostic evidence. It
is neither an issue-completion requirement nor an automatic production/release
veto. Replace autonomous-completion promises with an explicit
`waiting_for_operator` state for human-owned steps; do not retry them in a loop.

## Dependencies

ADR-0105 supersedes ADR-0101's mandatory exact-candidate release clause while
retaining its cost-saving manual-only CI trigger. Tracker creation remains
pending explicit outward-write authorization.

## Acceptance

- [x] Active governance requires one visible outcome and an early hard live-demo
  checkpoint for every delivery package.
- [x] Nonblocking review findings leave the active package instead of reopening
  a review-everything loop.
- [x] Exhaustive coverage and compatibility remain opt-in diagnostics and their
  absence does not force a `NO-GO`.
- [x] Human-owned transitions use `waiting_for_operator` and are not retried in
  an unattended loop.
- [x] Contributor, release, north-star, and agent instructions agree.
