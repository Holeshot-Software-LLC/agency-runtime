---
title: "Worklog: Preserve 10k routing headroom"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [performance, routing, retrieval, correctness]
related:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: eec520710c1629679a5e7063606cef2fb3bb49ae
short: eec5207
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
---

# Worklog: Preserve 10k routing headroom

## Purpose

Restore material scheduling headroom to the fixed 10,000-agent semantic
retrieval gate after an unchanged current-source evaluation exceeded its
150-millisecond warm ceiling.

## Approach

Profiling showed cosine scoring consumed 92.6 percent of warm time because each
of 3,750 eligible agents walked roughly 109 embedding dimensions while the
query had 49. Compiled agent vectors now remain immutable feature-addressable
maps, and cosine scoring walks the smaller vector. Revision identity validation,
support filtering, ordering, thresholds, samples, and cache authority are
unchanged.

## Challenges encountered

The first unchanged five-sample arm failed at 181.144 milliseconds and its
unchanged rerun passed at 127.495 milliseconds. That variance was real evidence
of inadequate margin, not permission to weaken the benchmark. The prototype's
mutable dictionaries also contradicted the compiled-index immutability
contract, so the final implementation uses read-only mapping proxies.

## Decisions and alternatives

The fixed benchmark was not relaxed. Positive trust caching and skipped
revision validation were rejected. Exact comparison with the former scoring
algorithm produced a maximum delta of 0.0 and retained the same selected-result
hash.

## Verification

- Final immutable-map 10,000-agent control: 7,839.770 ms cold, 53.825 ms warm
  p95 across five samples, and 167.817 MiB peak.
- Correctness and determinism: passed; selected-result hash
  `9214506c8a46c50e1cff4b2e0793127935c10f8f092d5a8597c8623cf4f69f60`.
- Semantic, selector, and no-match fallback suite: 60 passed.
- Ruff check, format check, documentation validation, and diff check: passed.

## Follow-ups

AR-140 remains open for supported-runner evidence and the separately measured
stable contractor/no-op reconciliation costs.
