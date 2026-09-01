---
title: "AR-358: Installers leave their trust chains trusted; doctor offers the fix"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [installer, doctor, trust-chain, operations]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-358
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/428
depends_on: []
blocks: []
---

# AR-358: Installers leave their trust chains trusted; doctor offers the fix

## Problem

The storage/executable trust rules (final parent dir mode 700, no
group-writable ancestors, no group/other-writable executables) are
enforced at read time but never established at write time, so every
external writer breaks them and an operator rediscovers the chmod
dance by forensics. Measured three separate times during the
2026-09-01 deploy alone: the Claude Code auto-updater left the
`~/.npm-global/@anthropic-ai` tree group-writable (canary
`group_writable: 14/16`), `npm install -g openclaw` left
`openclaw.mjs` group-writable (probe: "executable artifact permits
group or other writes"), and `claude plugin update` recreated
non-700 cache directories (`wiring unavailable — the host wiring file
is not trusted`). Session memory records each rediscovery costing
15-60 minutes.

## Current state

The fixes are operator lore (umask 077 + `chmod -R g-w` +
`find … -type d -exec chmod 700`), living in session memory and
handoff capsules instead of the product.

## Approach

Two layers: (1) every Agency installer/updater step normalizes the
permissions of exactly the trees it writes or depends on before the
trust probe runs (it knows the chains — marketplaces, plugin caches,
launcher trees, and the host executable chains it probes); (2)
`agency doctor` gains a `--fix-perms` (or equivalent consented) mode
that applies the same normalization to the known chains instead of
only diagnosing, with a dry-run listing. Never touch paths outside
the known chains.

## Dependencies

- None.

## Acceptance

- [ ] A fresh `agency install`/`--agent` run on trees freshly broken by
      npm or the claude auto-updater passes its own trust probes
      without manual chmod.
- [ ] `agency doctor` can list and, with consent, repair permission
      breaks on the known chains only.
- [ ] Regression tests cover the three measured break shapes.
