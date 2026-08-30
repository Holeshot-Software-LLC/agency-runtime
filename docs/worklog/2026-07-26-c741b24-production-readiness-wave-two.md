---
title: "Worklog detail: Complete production readiness hardening wave two"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [production-readiness, security, dashboard, observability, performance]
related:
  - docs/analysis/2026-07-26-production-readiness-review.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c741b24
short: c741b24
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-133-atomic-finalization-evidence.md
  - docs/roadmap/issue-AR-134-enforce-sqlite-currentness-invariants.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-136-persist-native-child-correlation.md
  - docs/roadmap/issue-AR-137-complete-dashboard-collections.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-139-restore-release-asset-budget.md
  - docs/roadmap/issue-AR-140-scale-routing-and-retrieval.md
  - docs/roadmap/issue-AR-141-restore-compatibility-consolidate-runtime.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
---

# Worklog detail: Complete production readiness hardening wave two

## Purpose

Close the independently reproduced second-wave transaction, native-host,
dashboard, observability, compatibility, and performance defects while
preserving a truthful hard checkpoint before installed dogfood.

## Approach

Finalization now commits one prevalidated bounded transaction. Native-child
authority is a durable, expiring, single-use Store scope, and ZCode owns an
exact reversible seven-event installation contract. Dashboard collections are
paginated and revision-bound; refresh commits one validated snapshot, rejects
stale generations, preserves interaction state, and exposes safe request IDs.

Content-free observation envelopes now correlate dashboard, HTTP, MCP, hooks,
Store latency/failures, and hiring outcomes. Semantic indexes are keyed by
exact revisions, the CLI version path defers heavy imports, deprecated public
wrappers are restored, and canonical helpers replace reviewed duplication.
The cached routing path removes redundant roster work and uses a recursively
detached JSON-like clone while preserving caller-mutation isolation.

Persistent CLI mutations are annotated centrally and fail closed unless a
non-exporting OS-backed operator-presence verifier succeeds. No production
verifier exists yet, so this intentionally blocks fresh autonomous install
instead of substituting a static confirmation or bearer.

## Challenges encountered

One combined five-minute test arm timed out without a result, so it is not
counted; its exact components passed in independent bounded suites. The cached
routing gate initially failed at 2.462 and then 3.096 ms. Profiling identified
duplicate roster identity work and generic deep-copy bookkeeping. Removing
those costs produced five unchanged median p95 controls from 1.531 to 1.795 ms
without changing the 2.0 ms threshold.

## Decisions and alternatives

ADR-0093 governs atomic finalization, ADR-0094 durable child correlation,
ADR-0095 complete dashboard collections, and ADR-0096 genuine operator
presence. Positive trust caching, threshold relaxation, static confirmation,
and model-callable mutation capabilities were rejected.

## Verification

- Authority package: 110 passed.
- Native-hook and ZCode package: 167 passed.
- Transaction, observability, MCP, and HTTP package: 147 passed, 8 skipped.
- Dashboard server package: 134 passed, 3 skipped.
- Browser interaction suite: 82 passed.
- Distribution and release package: 101 passed.
- Routing evaluation suite: 19 passed, including the unchanged performance gate.
- Selector cache correctness: 35 passed; final focused cache file: 9 passed.
- Ruff check and format check passed across 558 files.
- Documentation validation passed for 368 maintained Markdown files.
- git diff --check passed.

## Follow-ups

AR-143 still needs a genuine production OS-backed operator-presence verifier.
AR-137 needs explicit 263/1,001-row and concurrent-insert paging regressions;
AR-138 needs fresh installed desktop/mobile accessibility QA. AR-119 and
AR-125 still require a benchmark-valid matched corpus and current installed
host evidence. Tracker creation/closure, push/PR, hosted checks, normal-profile
Codex trust, and publication remain authorization or human-presence boundaries.
