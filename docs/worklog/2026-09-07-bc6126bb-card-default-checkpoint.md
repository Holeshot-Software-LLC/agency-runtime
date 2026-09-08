---
title: "Freeze corrected read-only card defaults"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [cli, handoff, review]
related:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
  - docs/roadmap/handoffs/issue-AR-251.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: bc6126bbced4e0f104987301d37575a98f22def4
short: bc6126bb
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/753
related_issues:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
---

# Worklog detail: docs(AR-251): align checkpoint with governed card defaults

## Purpose

Project the reviewed TTY correction into the current issue, capsule and public
changelog without rewriting the faithful initial implementation history.

## Approach

Freeze corrected source `54bdff1f` and immediate ledger `a6c34707`. State
automatic TTY cards, explicit `--card`/`--no-card`, unchanged non-TTY/plain
bytes and JSON precedence, and existing redaction boundaries.

## Challenges encountered

Omitting `--card` is not a complete plain-output alternative on a TTY. Current
records and source now point to `--no-card` or existing `--json` instead.

## Decisions and alternatives

Follow ADR-0154 directly; no new policy exception or ADR. Keep the initial
default-false checkpoint explicitly historical. AR-251 remains `in_progress`.

## Verification

No tests, CI, acceptance, installed CLI, native hosts, or providers ran.
Formatting, mechanical parser artifact generation, source review and record
maintenance do not constitute runtime verification.

## Follow-ups

Parent coordinates publication and later authorized verification. Original
acceptance boxes remain unchanged; no closure or installed-delivery claim.
