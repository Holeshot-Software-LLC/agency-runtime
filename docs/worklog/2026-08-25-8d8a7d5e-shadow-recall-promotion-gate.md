---
title: "Worklog detail: Add shadow recall promotion gate"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [workforce, embeddings, retrieval, evaluation]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/decisions/0164-use-dense-embeddings-only-for-workforce-recall.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 8d8a7d5e
short: 8d8a7d5e
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
---

# Worklog detail: Add shadow recall promotion gate

## Purpose

Make AR-266's last live acceptance box reproducible and fixed before provider
results are observed. The command is an explicit promotion gate, not a general
staffing or task-outcome evaluation.

## Approach

Added `agency eval shadow-recall` with an exact live-inference confirmation. It
runs four identity-free vocabulary-gap cases under Codex, Claude, Hermes, and
OpenClaw host contexts through the production shadow recall path. The report
grades exact typed-baseline retention, category non-regression, zero activation
of forbidden, ineligible, or disabled workers, complete-roster receipts,
provider fallback, cold/warm cache behavior, a disabled-worker catalog-identity
rebuild, and at least one recovered predeclared target. It returns only bounded
content-free evidence and never promotes the runtime configuration itself.

## Challenges encountered

The runtime intentionally discards reranked candidates in shadow mode. The
evaluator therefore uses the production empty shadow application result for
activation gates while separately treating an applied reranker receipt as proof
that its closed parser returned every offered discovery exactly once. This
preserves shadow isolation instead of adding an evaluation-only bypass.

## Decisions and alternatives

A one-off shell script was rejected because it would not freeze targets and
thresholds before the live run. Reusing the configured workforce-selection
corpus alone was rejected because it cannot expose retrieval value without
confounding planner and recruiter variance. The fixed evaluator calls only the
explicit embedding and recall-reranker routes and leaves staffing authority
with the unchanged recruiter and verifier described by ADR-0164.

## Verification

- 106 focused evaluator, CLI/parser, hybrid-recall, and workforce-inference
  tests pass with warnings treated as errors.
- Focused Ruff check and format-check pass.
- Documentation metadata, policy availability, worklog, and link validation
  pass for 803 Markdown files.
- `git diff --check` passes.

## Follow-ups

Run the exact-confirmed live matrix. Promote only Agency's dense-recall mode to
`additive` if every predeclared gate passes, then run a changed bounded smoke
and record the provider evidence under AR-266.
