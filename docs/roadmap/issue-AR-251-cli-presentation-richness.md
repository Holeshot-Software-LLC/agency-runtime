---
title: "AR-251: CLI presentation richness (sub-issue 10 of AR-236)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [cli, dashboard, parity, presentation, card, sub-issue]
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
  - agency_runtime/cli/_render.py
  - agency_runtime/cli/workforce_commands.py
  - agency_runtime/cli/parser.py
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-251
priority: p2
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/260"
depends_on: []
blocks: []
---

# AR-251: CLI presentation richness (sub-issue 10 of AR-236)

## Problem

The CLI output is tab-separated text. The dashboard renders cards with
grouped metadata. The user asked for the CLI to be "pretty too."

## Current state

- AR-237 introduced `agency_runtime/cli/_render.py` with a plain-text card
  layout (dividers, tab-aligned fields, sections) and a `--card` flag for
  hiring commands.
- ADR-0154 records the decision to use plain-text cards over a `rich`
  dependency (zero-dependency install property).

## Approach

Extend `--card` to the remaining CLI commands. This slice adds card mode
to `workforce list` (one card per worker). The hiring commands already
have it from AR-237.

## Acceptance

- [x] ADR-0154 records the plain-text card decision.
- [x] `workforce list --card` renders one card per worker.
- [ ] Extending `--card` to remaining commands (roster, policy, config) is
      an incremental follow-up; the rendering infrastructure is in place.
