---
title: "AR-403: Reuse roster embeddings across native hook processes"
status: in_progress
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [performance, workforce, recall]
related:
  - docs/decisions/0218-cache-only-roster-vectors-across-hook-processes.md
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-403
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/668
depends_on: []
blocks: [AR-404]
---

# AR-403: Reuse roster embeddings across native hook processes

## Problem

Native hooks start fresh processes, but hybrid recall cached the entire roster's
embeddings only in a process-local two-entry cache. Repeated unchanged catalog
embedding can dominate staffing. The supplied September 2–5 failure snapshot
contains 11 timed embedding attempts with median 40.44 s; that small biased
sample is a lead, not a current end-to-end benchmark.

## Current state

The owner requested a performance pass that preserves staffing/hiring quality.
Phase: demo_ready. Fixed-response fresh-process regression proves query-only
reuse preserves exact candidates. A current live pair measured recall at
63.620 s cold versus 8.804 s warm, with 283 versus one embedding input.
The retained JSON under acceptance/evidence/AR-403-recall-performance-20260905.json
includes all stage counts/times and limitations. Fifteen of sixteen live
additions overlap; no end-to-end staffing or live quality-equivalence claim.

## Approach

Add a disposable private two-slot cache of exact normalized roster document
vectors. Bind reuse to store namespace, roster projection, generation, provider
endpoint/model/dimensions and normalization identity. Expire after one hour;
validate the actual model on each new query. Never persist queries, prompts,
plans or decisions. Keep recruiter, strict critic and hiring audits unchanged.
Retain bounded recall counters on failure receipts to avoid evidence blind spots.

## Dependencies

AR-401 independently bounds total inference time. AR-400 owns PR delivery,
installation and all-harness smoke. No provider configuration change is implied.

## Acceptance

- [ ] Fresh independent processes embed unchanged roster documents once, embed every new query, and return identical recall candidates from lossless vectors.
- [ ] Changed identities, roster projections, expiry, corruption, model mismatch and unsafe filesystem targets cannot reuse stale or unsafe vectors; cache faults never block otherwise valid recall.
- [ ] Current cold/warm provider measurements record stage timings, input counts, cache hits and limitations without claiming simulated or historical timing as live speedup; all existing staffing quality gates remain enabled.
