---
title: "Worklog: fresh-process roster-vector reuse"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [performance, workforce]
related:
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
  - docs/decisions/0218-cache-only-roster-vectors-across-hook-processes.md
supersedes: []
superseded_by: null
type: worklog
commit: e9d8ecea1fe45e7ddcb2566c5433b71128c43822
short: e9d8ecea
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/669
related_issues:
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
---

# Worklog: fresh-process roster-vector reuse

## Purpose

Remove repeated invariant roster embedding from short-lived native hooks without
changing staffing or hiring quality.

## Approach

ADR-0218: two private fixed disk slots, exact float64 vectors, one-hour TTL,
identity binding and per-query actual-model/dimension validation. The explicit
Store scopes the cache even under atomic preflight's deferred evidence writes.
Failure receipts preserve bounded recall counters.

## Challenges encountered

The full preflight regression caught a disabled cache under deferred writes.
Baseline lint/format defects were corrected; deadline complexity was factored,
not suppressed. The conformance manifest now detects restoration of the
superseded domain veto. The isolated evaluator required a copied-interpreter
dev environment and umask 077; its next baseline found a legacy critic fixture
still expecting a domain waiver, which remains to update to a capability waiver.

## Decisions and alternatives

Do not cache user queries or staffing decisions, lower precision, skip critics,
change provider profiles or increase the lease.

## Verification

145 targeted tests, 94 preflight/receipt/manifest tests with one skip, 138 JS
tests and routing evaluation pass. Lint/format are clean. The first fast spine
passed 1003 with three skips and one obsolete mutation anchor failure; the anchor
is corrected. Full fast-spine rerun, conformance and live timing remain due.

## Follow-ups

AR-400 owns merge/install/all-host smoke; AR-403 owns current cold/warm timing.
No live performance or deployed completion claim is made at this checkpoint.
