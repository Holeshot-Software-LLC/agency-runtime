---
title: "Worklog detail: Second 19-case Agency pass"
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
commit: 0dfe777e87e0137433b199c015fcd994740c6974
short: 0dfe777
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Second 19-case Agency pass

## Purpose

Preserve the second complete 19/19 Agency matched-selection observation and
the exact remaining upstream benchmark-validity blocker.

## Approach

The unchanged 19-case Windows corpus ran from clean ledger `3e34c6f` with the
audited roster, provider, model, low effort, one-call fast budget, and 15000 ms
cold gate. Both streams were captured outside the repository before parsing,
and the exact projection was verified byte-for-byte.

## Challenges encountered

Agency passed every gate, but the application-observability upstream arm
returned unknown disabled shadows. That one malformed arm invalidated the
complete benchmark and prevents comparative interpretation.

## Decisions and alternatives

No product, policy, parser, coverage, latency, or call-budget rule changed.
There was no Agency failure to confirm. The malformed upstream arm remains a
validity failure, never a loss, and no superiority claim is made.

## Verification

- The process returned status 1 in 406.071759 seconds; its 1,195,829-byte
  stdout had SHA-256
  `2e051f5aa2aa7b158a2ba799fde3ca9ff0e413a89fd587d0be740d090063b530`
  and stderr was empty.
- The 13,313-byte exact projection had SHA-256
  `bab3fbf0c735603439914d284afc5a044d154b6e56f27715ef8dbdefbc6400c6`
  and matched the canonical issue byte-for-byte.
- Agency passed 19/19 with 19/19 typed coverage, complete disabled disclosure,
  p95/max 12942.243 ms, and zero unsafe selections.
- All 38 arms retained the exact provider/model receipt, one call, applied
  inference, and 15000 ms binding.
- Exactly one malformed upstream arm kept the benchmark invalid.
- Metadata, policy availability, worklog-current, docs validation, and
  `git diff --check` passed.

## Follow-ups

- Run one further unchanged complete corpus seeking 19 valid upstream arms.
- Do not reinterpret malformed upstream output or claim Agency is better.
