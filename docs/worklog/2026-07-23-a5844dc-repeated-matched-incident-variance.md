---
title: "Worklog: Record repeated matched incident variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, stability, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: a5844dc1e46dd01c880961e4bc4483acfda64a8a
short: a5844dc
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record repeated matched incident variance

## Purpose

Run the next unchanged matched active-incident confirmation, compare a repeated
safe abstention with the accepted cold diagnostic shape, and preserve the exact
remaining AR-119 blocker without advancing to contractor lifecycle work.

## Approach

The matched Windows case retained the predeclared 15000 ms cold gate, one-call
fast budget, `codex-subscription`, requested and actual `gpt-5.6-luna`, low
reasoning effort, explicit-model receipts, and applied inference. Both process
streams were captured outside the repository before parsing. After Agency
abstained, one cold Agency-only diagnostic used the identical case snapshot and
matched configuration to expose the governed plan and proposal shape.

## Challenges encountered

The valid matched benchmark repeated `selection_margin_too_low` with no unsafe
selection. The score document does not retain rejected planner units, so the
cold diagnostic cannot replace matched evidence. It did reproduce the prior
accepted two-unit plan structure and selected `incident-responder` with margins
0.205 and 1.0, confirming bounded plan/proposal variance rather than a stable
deterministic defect.

## Decisions and alternatives

No product, policy, parser, coverage, latency, or call-budget rule changed. The
evidence did not justify a scenario route, weaker typed coverage, a higher cold
gate, or another inference call. The next matched confirmation should preserve
the full Agency outcome through a pass-through diagnostic wrapper before score
projection, allowing an exact rejected-plan comparison if abstention repeats.

## Verification

- The matched process finished in 23.989 seconds, returned status 1, emitted
  709,281 stdout bytes and zero stderr bytes, and both saved hashes reproduced.
- The benchmark was valid; Agency failed closed only on selection margin at
  9135.924 ms with zero forbidden, ineligible, or conflict selections.
- The 639-byte exact projection reproduced with SHA-256
  `1a78c811dda3971aad99a4c31583fa2aa53783322d945aca9c711eff8c7e32cf`.
- The 23,475-byte diagnostic reproduced the prior accepted controlled plan
  shape and had SHA-256
  `59473e82589dd14caa5b9883c7fa15a8a6c1dc1b87b6163758a3b8b4c8cf1c5b`.
- Metadata, policy availability, worklog currency, documentation validation,
  evidence reproduction, and `git diff --check` passed before the recovery
  commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Preserve the complete Agency outcome during the next
bounded matched incident confirmation; run a full unchanged corpus only if the
Agency arm passes.
