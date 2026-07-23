---
title: "Worklog detail: Confidence-abstention recovery"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, inference, workforce, selection, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
supersedes: []
superseded_by: null
type: worklog
commit: fc9c453b360f2274b4afd03ffa4df3ce61e97aa0
short: fc9c453
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Confidence-abstention recovery

## Purpose

Retain the complete instrumented outcomes for the two Agency confidence
abstentions in the newest 17/19 corpus and determine whether either observation
repeated under unchanged matched controls.

## Approach

The run started from clean ledger `27fcecc` after observational telemetry
confirmed that the retained 50-percent checkpoint was already satisfied. A
pass-through Agency router wrote each complete outcome before returning it to
the normal scorer. The outer wrapper captured stdout and stderr before parsing,
and the parser verified the atomic manifest, exact cases, matched controls,
baseline hashes, complete plans, proposal scores, confidence, margins, and
scorer projection.

Both Agency arms accepted. Application observability used four units and the
broad application used seven; every unit had confidence and margin 1.0. Agency
passed 2/2 with complete typed coverage and zero forbidden, ineligible, or
conflict selections. The bounded benchmark was valid, but it does not replace a
complete-corpus result.

## Challenges encountered

The accepted and newest failed complete-corpus baselines preserve scorer
projections but not complete planner units. Their final selected sets can be
compared, but stronger unit-by-unit plan-shape comparison is unavailable.

## Decisions and alternatives

No product or selection-policy change was made because both observations
recovered under unchanged controls. Treating the bounded result as evidence
that Agency is better was rejected; the complete corpus has varied, and no
complete run has yet produced 19 benchmark-valid upstream arms.

## Verification

- The zero-call launch audit bound clean `27fcecc`, the exact two cases,
  generation 561, 272 workers, 247 tools, codex-subscription,
  `gpt-5.6-luna`, low effort, and one configured fast call.
- The process returned status 0 in 57.628651 seconds; 723,247-byte stdout had
  SHA-256
  `707f4a23fb46e3ea2d7ce85afb83dc0323e6cfcb9488e5aa32d6d3ad3ee5e320`,
  and stderr was empty.
- Both complete outcome files existed before parsing; independent hashes
  matched the atomic manifest.
- The 2,119-byte exact projection had SHA-256
  `753f83abba79d4eb7e21babd956ff54e35d9fabe906aa62d4414d38ac15528f9`.
- Metadata, policy availability, worklog-current, full docs validation, and
  `git diff --check` passed; docs validation covered 318 Markdown files.

## Follow-ups

- Run one further unchanged complete 19-case Windows corpus and retain the
  exact 19-line projection.
- Keep malformed, no-response, and timed-out upstream arms as benchmark
  validity failures, never losses.
