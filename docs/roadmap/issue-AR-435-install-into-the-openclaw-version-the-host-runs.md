---
title: "AR-435: Install into the OpenClaw version the host runs"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [openclaw, installer, hosts, reliability]
related:
  - docs/decisions/0247-accept-any-stable-openclaw-at-or-above-the-audited-minimum.md
  - docs/roadmap/issue-AR-267-accept-openclaw-numeric-package-revision.md
  - docs/roadmap/issue-AR-433-name-the-neighbour-a-wrong-neighbour-veto-points-at.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/TROUBLESHOOTING.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-435
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/851
depends_on: []
blocks: []
---

# AR-435: Install into the OpenClaw version the host runs

## Problem

Reinstalling the a354e9a5 runtime on 2026-09-10 registered claude, codex,
hermes and zcode but refused openclaw at the fail-closed gateway guard with
`host_capability_unproven`: "OpenClaw hook compatibility could not be proven.
Agency Runtime requires OpenClaw 2026.8.2 or newer (stable)." The host runs
`OpenClaw 2026.9.3 (1391f7c)`, which is newer and stable, but
`openclaw_version_supported` accepted only the exact `2026.8` release line
(`observed[:2] == minimum[:2]`), so the message and the rule disagreed and the
openclaw plugin tree stayed on the previous runtime digest while every other
host moved. The owner's decision: the installer must install into whatever
OpenClaw version is on the host machine.

## Current state

Repaired on branch `claude/ar435-openclaw-newer-lines-20260910`: any stable
OpenClaw at or above the audited minimum is accepted; prereleases and older
versions are still refused; the parser and the gateway guard are otherwise
unchanged. The troubleshooting text that still described a `2026.7.x` line pin
is corrected. Focused installer suites pass.

## Approach

Compare the parsed stable version against the minimum as a whole
(`observed >= minimum`) instead of pinning the release line. Keep the minimum,
the prerelease refusal, the stopped-gateway consent rule and the post-install
battery and runtime inspection as the hook-compatibility evidence. Record the
decision in ADR-0247.

## Dependencies

AR-267 retired the earlier `2026.7`-only contract. AR-433's reinstall is the
observation. Live proof of the openclaw reinstall belongs to the AR-404 host
package.

## Acceptance

- [ ] `openclaw_version_supported` accepts the exact host string
      `OpenClaw 2026.9.3 (1391f7c)` and any later stable version, and still
      refuses prereleases and versions below `2026.8.2`.
- [ ] Focused installer suites and the named fast checks pass, and the
      troubleshooting text matches the rule.
- [ ] One openclaw reinstall on the host completes registration with the
      a354e9a5-or-later runtime and a fresh native openclaw turn shows the new
      runtime live, with tracker and worklog parity.
