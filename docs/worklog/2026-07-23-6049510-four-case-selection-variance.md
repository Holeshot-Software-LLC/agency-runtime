---
title: "Worklog detail: Four-case selection variance"
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
commit: 6049510e218e225bfb800846392ba14f694ebf0c
short: 6049510
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Four-case selection variance

## Purpose

Preserve the further unchanged complete matched-selection corpus before
confirming its four distinct non-safety Agency failures.

## Approach

The 19-case Windows corpus ran from clean ledger `bb876f8` with the audited
roster, provider, model, low effort, one-call fast budget, and 15000 ms cold
gate unchanged. Both streams were captured outside the repository before
parsing, and the exact projection was verified byte-for-byte.

## Challenges encountered

Agency safely abstained on installed release and runtime routing, omitted the
required disabled-winner disclosure while safely abstaining on disabled LSP,
and exceeded the latency gate with the correct broad-application team. Four
upstream arms were malformed, so the benchmark remained invalid.

## Decisions and alternatives

No product or selection-policy change was made from one complete-corpus
observation. The next package is an exact four-case instrumented confirmation
that preserves complete outcomes before scoring. Scenario routing, coverage
relaxation, latency increase, an extra provider call, and treating upstream
errors as losses were rejected.

## Verification

- The process returned status 1 in 454.014647 seconds; its 1,182,655-byte
  stdout had SHA-256
  `b7d2f45e06703901b92d7c63272c4f6852c864b800d09915c1bb26792429e35b`
  and stderr was empty.
- The 12,702-byte exact projection had SHA-256
  `c0ae85f40b8667e21479d97693fb52e3f3c2dad4020f45b35a1d635f4b73545c`
  and matched the canonical issue byte-for-byte.
- All 38 arms retained the required explicit provider/model receipt, one call,
  applied inference, and 15000 ms binding.
- Agency scored 15/19 with 17/19 typed coverage and zero unsafe selections.
- Four malformed upstream arms kept the complete benchmark invalid.
- Metadata, policy availability, worklog-current, docs validation, and
  `git diff --check` passed.

## Follow-ups

- Instrument exactly installed release, runtime routing, disabled LSP, and
  broad application under unchanged matched controls.
- Keep malformed upstream arms as benchmark-validity failures and do not claim
  Agency is better.
