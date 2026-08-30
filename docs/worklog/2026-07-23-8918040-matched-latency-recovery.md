---
title: "Worklog detail: Matched latency recovery"
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
commit: 89180406a56b575c969b0dccbe60ae85f4dcc10e
short: 8918040
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Matched latency recovery

## Purpose

Preserve the next unchanged complete matched-selection corpus and the bounded
confirmation of its two Agency latency failures without converting provider
variance into a product or policy change.

## Approach

The complete 19-case Windows corpus ran from clean ledger `fe68e10` with the
audited roster, provider, model, low effort, one-call fast budget, and 15000 ms
cold gate unchanged. Both streams were captured as raw bytes outside the
repository before parsing, and the exact 19-line projection was verified
byte-for-byte.

The two accepted Agency outcomes that exceeded the latency gate were then run
through a zero-call-validated instrumented matched package. The pass-through
router durably wrote both complete outcomes before scoring.

## Challenges encountered

All 19 complete-corpus Agency arms were correctly selected, fully typed, and
safe, but brand/whimsy and PostgreSQL analysis exceeded the fixed latency gate.
Three upstream arms returned unknown disabled shadows, so the complete
benchmark remained invalid. The bounded confirmation passed both Agency cases
within the same latency gate.

## Decisions and alternatives

No product, selection-policy, parser, typed-coverage, latency, or call-budget
rule changed. The identical bounded recovery and earlier complete-corpus passes
establish latency variance rather than a repeatable governed defect. Raising
the gate, adding a call, weakening coverage, scenario routing, and treating
malformed upstream arms as losses were rejected.

## Verification

- The complete process returned status 1 in 439.177328 seconds; its
  1,186,787-byte stdout had SHA-256
  `f5b8002c468e5bebef75db2f79aba3c7d3757bb61ed4fb26814b699a69f270bb`
  and stderr was empty.
- The complete 12,771-byte projection had SHA-256
  `d71a07c81d04dd48a23206e4fff5752a181bc4e2dab2df06dd3c6ddf6bd3bdfe`
  and matched the canonical issue byte-for-byte.
- Agency scored 17/19 with 19/19 typed coverage and zero unsafe selections;
  the two misses were latency-only accepted outcomes.
- The bounded process returned status 0 in 46.569601 seconds; its 711,421-byte
  stdout/report had SHA-256
  `f1326cd8de2848f4ee9d954e8e22d944a84875f82f1ae28789dfde48e9ea1608`.
- The bounded benchmark was valid, Agency passed 2/2, and every captured unit
  had confidence and margin 1.0.
- Metadata, policy availability, worklog-current, docs validation, exact
  projection comparison, and `git diff --check` passed.

## Follow-ups

- Run one further unchanged complete 19-case Windows corpus from the new clean
  ledger checkpoint.
- Keep every malformed upstream arm as a benchmark-validity failure and do not
  claim Agency is better.
