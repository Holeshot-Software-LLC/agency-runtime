---
title: "AR-363: Attest deployed fixes with per-host witness manifests"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [install, drift, attestation, baseline]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/roadmap/issue-AR-358-installer-doctor-trust-chain-self-healing.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-363
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/436
depends_on: []
blocks: []
---

# AR-363: Attest deployed fixes with per-host witness manifests

## Problem

Nothing attests that the runtime a host actually executes carries the
fixes main claims to ship. Measured 2026-09-01: a live session ran
launcher projection `e5e2e193` while the last install had published
`8698cca9` — stale hooks executing pre-fix code, detected only because
a SessionStart notice happened to say so. Version stamps prove what was
installed, not that each documented fix's load-bearing code is present
in what runs.

## Current state

The battery baseline records harness versions per host. Fix presence
is unverified; drift between published projection and wired host is
surfaced ad hoc.

## Approach

Adopt a witness layer (concept lifted from ruflo's verification
system, owner-approved 2026-09-01):

- A registry of documented fixes, each with the file and a load-bearing
  marker (e.g. AR-345's clause-boundary regex, AR-346's
  `_FAIL_OPEN_RUN_STATUSES`).
- Per-host manifests recording projection digest + per-fix marker
  verification for the projection each host's wiring points at,
  written at install/battery time.
- An append-only history log per host so drift can be bisected to the
  snapshot that introduced it.
- The battery fails a host whose wired projection lacks a registered
  fix marker or diverges from the published projection.

## Dependencies

- Extends the AR-337 battery-on-version-change discipline.

## Acceptance

- [ ] Each host's wired projection is attested against the fix registry
      at battery time; a missing marker or projection drift fails that
      host.
- [ ] The stale-hook shape (wired digest != published digest) is
      detected by the witness check, covered by a regression test.
- [ ] Witness results append to a per-host history usable for bisecting.
