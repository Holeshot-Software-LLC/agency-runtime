---
title: "AR-114: Make Codex hook activation part of installation"
status: in_progress
category: roadmap
created: 2026-07-20
updated: 2026-07-20
tags: [installation, codex, hooks, trust, canary]
related:
  - README.md
  - agency_runtime/cli/install_commands.py
  - agency_runtime/core/installer_inventory.py
  - agency_runtime/core/canary.py
  - docs/RELEASE_CHECKLIST.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-114
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/123
depends_on: []
blocks: []
---

# AR-114: Make Codex hook activation part of installation

## Problem

`agency install` can register and enable the Codex plugin while Codex still
requires the user to review and trust its command hooks. The installer reports
native registration as successful, but its inventory hard-codes hook trust as
`unverified` and cannot prove that a normal real-profile Codex session will run
Agency preflight and finalization. Users can therefore finish installation
without receiving Agency headers or specialist routing.

## Current state

The CLI prints a manual `/hooks` instruction and the isolated canary bypasses
hook trust inside a disposable profile. That proves the packaged hooks, not the
user's normal Codex profile. Status can distinguish the unverified maturity but
the top-level install result still overstates completion.

## Approach

Make hook approval an explicit, guided Codex activation phase. Preserve Codex's
security boundary: never edit its trust store or silently use the dangerous
trust bypass for a real profile. Report registration and activation separately,
provide a resumable verification command, and accept readiness only from a
normal-profile canary that runs without the bypass and records current-profile
evidence. Interactive installation should guide the user through `/hooks` and
then run that proof; non-interactive and JSON modes should return structured
`activation_required` state and the exact next command.

## Dependencies

AR-03 owns native host integration, AR-17 owns release readiness, and AR-79 owns
installed Codex header proof. ADR-0036 governs host-canary attestations.

## Acceptance

- [ ] Codex installation never claims ready while hook approval is unverified.
- [ ] The installer clearly separates installed, activation-required, and ready states.
- [ ] A guided path incorporates `/hooks` approval without modifying Codex trust state.
- [ ] A current-profile Codex canary runs without `--dangerously-bypass-hook-trust`.
- [ ] Only current-profile routing, load, finalization, and valid-header evidence establishes readiness.
- [ ] JSON, human CLI, status, doctor, dashboard, and public documentation agree.
- [ ] Windows and Linux tests cover interactive, non-interactive, trusted, untrusted, and interrupted activation.
