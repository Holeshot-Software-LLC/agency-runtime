---
title: "AR-411: Retain recall catalog identity in failure receipts"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [performance, observability, recall, privacy]
related:
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
  - docs/decisions/0218-cache-only-roster-vectors-across-hook-processes.md
  - docs/roadmap/handoffs/issue-AR-411.md
  - agency_runtime/core/preflight_failure.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/routing_projection.py
  - tests/test_persistent_hybrid_recall_cache.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-411
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/746
depends_on: []
blocks: []
---

# AR-411: Retain recall catalog identity in failure receipts

## Problem

Hybrid recall emits a content-free catalog identity with its embedding attempt,
but the terminal-preflight projection discards it. Repeated cold embedding
receipts retain counts and cache-hit flags without the identity needed to
distinguish reuse of one catalog from changes in the upstream key. This is an
observability gap, not proof that the persistent cache itself fails.

## Current state

The production producer in `workforce/inference.py` constructs the key with
`_document_hash`: the literal `sha256:` prefix plus 64 lowercase hexadecimal
characters. `workforce/routing_projection.py` already emits it. The failure
projection's `_recall_performance_counts` keeps input/call counts and cache
hit but omits this field. Lower-level recall fixtures can use arbitrary opaque
identifiers; those are not admitted to this durable projection.

The implementation preserves only this exact digest on `recall_embedding`
attempts. Invalid values are omitted without discarding the remaining attempt
or failure receipt. Written regressions cover retention, repeated/full-receipt
projection, invalid types/lengths/case, unrelated stages and continued omission
of query/path/vector fields. Per owner direction, tests and CI have **not run**.
Targeted static Ruff lint/format and diff checks pass; no installed receipt,
acceptance verdict or speedup is claimed. Status remains in_progress.

## Approach

Extend the existing bounded failure projection by one validated field. Do not
change the recall key, cache directory, TTL, eviction, embeddings, providers,
staffing/hiring policy or timing. Do not stringify, trim or normalize rejected
values. Only `sha256:[0-9a-f]{64}` passes unchanged, only for embedding attempts.
No raw paths, prompts, queries, catalog content, vectors, endpoints or
credentials are newly persisted.

This applies ADR-0218's existing content-free performance-evidence boundary
to metadata the producer already exposes. There is no new cache or staffing
authority and no new ADR.

## Dependencies

AR-403 owns the persistent cache and original measurements; this does not reopen
its acceptance or claim every later cold call is a defect. AR-410 filing #744
preceded this item's authorized tracker #746. Parent coordinates publication.

## Acceptance

- [ ] An exact lowercase SHA-256 catalog digest survives a recall-embedding
  attempt's terminal failure projection, including full-receipt validation.
- [ ] Invalid values and non-embedding stages omit the identity without losing
  remaining evidence; raw paths, prompts, queries and vectors stay excluded.
- [ ] Focused regression evidence and one newly produced failed-preflight
  receipt establish the behavior without changing cache or staffing policy.
