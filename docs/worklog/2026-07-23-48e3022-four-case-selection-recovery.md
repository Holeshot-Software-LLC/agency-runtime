---
title: "Worklog detail: Four-case selection recovery"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, inference, workforce, selection, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
supersedes: []
superseded_by: null
type: worklog
commit: 48e3022837e822ee82d51219854939ca410e901d
short: 48e3022
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Four-case selection recovery

## Purpose

Preserve complete plans and proposals for all four Agency failures in the
newest complete corpus before considering any selection-semantics change.

## Approach

A zero-provider-call validation bound installed release, runtime routing,
disabled LSP, and broad application to the unchanged roster, tools, provider,
model, latency gate, and call budget. It verified the scorer projections
against both the preserved 19/19 Agency corpus and the newest failed corpus.
The pass-through router wrote every complete Agency outcome before scoring.

## Challenges encountered

All four Agency cases recovered, while two upstream arms were malformed and
kept the bounded benchmark invalid. The disabled LSP case used a valid two-unit
plan that disclosed the disabled semantic winner and safely abstained when no
safe deterministic team existed for the second unit.

## Decisions and alternatives

No product, policy, parser, coverage, latency, or call-budget rule changed. The
immediate recovery establishes variance, not a repeatable governed defect.
Scenario routing, weaker coverage, a higher gate, an extra call, and treating
upstream errors as losses were rejected.

## Verification

- The process returned status 1 in 109.988309 seconds only because the matched
  benchmark was invalid; its 768,427-byte stdout/report had SHA-256
  `2bc25b57ea7b5d86b36d8ef38bba1c2d6d510a88358b62a28814ed892181ac93`.
- Stderr was empty, and all four complete Agency outcome files were present.
- The 3,350-byte exact projection had SHA-256
  `fb72cf528a86e079cee3b46e8cb60debaf803fa740826b845f006d6b2e239a50`
  and matched the canonical issue byte-for-byte.
- Agency passed 4/4 with complete typed coverage and disabled disclosure,
  p95/max 14074.396 ms, and zero unsafe selections.
- Two malformed upstream arms kept the bounded benchmark invalid.
- Metadata, policy availability, worklog-current, docs validation, and
  `git diff --check` passed.

## Follow-ups

- Run one further unchanged complete 19-case Windows corpus from the new clean
  ledger checkpoint.
- Keep malformed upstream arms as benchmark-validity failures and do not claim
  Agency is better.
