---
title: "AR-114: Make Codex hook activation part of installation"
status: in_progress
category: roadmap
created: 2026-07-20
updated: 2026-07-21
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

The CLI formerly printed an ambiguous manual `/hooks` instruction. In Codex
Desktop 26.715, that command opens connector setup and shows services such as
Zoom and Twilio rather than local command-hook trust. The actual review surface
for Codex CLI 0.144 is the terminal TUI's startup hook review or its own
`/hooks` command. The isolated canary bypasses hook trust inside a disposable
profile; that proves the packaged hooks, not the user's normal Codex profile.

## Approach

Make hook approval an explicit, guided Codex activation phase. Preserve Codex's
security boundary: never edit its trust store or silently use the dangerous
trust bypass for a real profile. Report registration and activation separately,
provide a resumable verification command, and accept readiness only from a
normal-profile canary that runs without the bypass and records current-profile
evidence. Interactive installation should identify the Codex terminal TUI,
distinguish it from Codex Desktop's connector-oriented `/hooks` screen, and
then run that proof; non-interactive and JSON modes should return structured
`activation_required` state, approval surface, launch command, and exact
verification command.

## Dependencies

AR-03 owns native host integration, AR-17 owns release readiness, and AR-79 owns
installed Codex header proof. ADR-0036 governs host-canary attestations.

## Acceptance

- [ ] Codex installation never claims ready while hook approval is unverified.
- [ ] The installer clearly separates installed, activation-required, and ready states.
- [ ] A guided path identifies the terminal TUI hook review without confusing it with Codex Desktop connector setup or modifying Codex trust state.
- [ ] A current-profile Codex canary runs without `--dangerously-bypass-hook-trust`.
- [ ] Only current-profile routing, load, finalization, and valid-header evidence establishes readiness.
- [ ] JSON, human CLI, status, doctor, dashboard, and public documentation agree.
- [ ] Windows and Linux tests cover interactive, non-interactive, trusted, untrusted, and interrupted activation.
