---
title: "Worklog detail: Bounded selection recovery"
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
commit: b8c1eca4dfef5889ae50b99a01dda47a11b1f05a
short: b8c1eca
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Bounded selection recovery

## Purpose

Preserve complete plans and proposals for the two failures in the newest
complete corpus before considering any selection-semantics change.

## Approach

A zero-provider-call validation bound exactly application observability and
selection-safety review to the unchanged roster, tools, provider, model,
latency, and call controls. The instrumented runner wrote each complete Agency
outcome before scoring, while the outer wrapper captured both process streams.

Both Agency arms accepted. Application observability used five units and
selection-safety review used one; every proposal had confidence and margin 1.0.

## Challenges encountered

Application observability has now accepted different valid bounded plan shapes
around complete-corpus abstentions. Complete-corpus baselines do not preserve
planner units, so stronger unit-by-unit comparison is unavailable.

## Decisions and alternatives

No product or selection-policy change was made. The immediate recovery of both
failures establishes variance rather than a repeatable general defect. A
scenario route, confidence relaxation, latency increase, or additional call
was rejected.

## Verification

- The process returned status 0 in 38.702201 seconds.
- The 712,543-byte stdout/report had SHA-256
  `5b8a2a7883ce7daeb78f39125815bebf6d18b317ceb6450ccd129e7b567b9ed6`;
  stderr was empty.
- The 1,180-byte exact projection had SHA-256
  `645d009288fec0942a32d4e0f611cc6cdad0e77d82fb63af09b93ca9d947d85f`.
- Both complete outcome hashes matched the parsed analysis.
- Metadata, policy availability, worklog-current, docs validation, and
  `git diff --check` passed; docs validation covered 320 Markdown files.

## Follow-ups

- Run one further unchanged complete 19-case Windows corpus.
- Keep malformed upstream arms as benchmark-validity failures and do not claim
  Agency is better.
