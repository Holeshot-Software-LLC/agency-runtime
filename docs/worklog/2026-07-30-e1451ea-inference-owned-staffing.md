---
title: "Worklog detail: fix(routing): require inference-owned staffing"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [routing, inference, staffing, delegation, conformance]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: e1451ea9c1c8a816b7b6d556c6306cf9f28ed8ce
short: e1451ea
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: fix(routing): require inference-owned staffing

## Purpose

Make the README's inference-first workforce claim true in production. A missing,
unavailable, or invalid provider decision must fail visibly without selecting,
recommending, delegating, or hiring a specialist.

## Approach

Workforce planning now returns explicit unavailable or invalid states instead
of invoking an offline staffing floor. Online plan parsing preserves only the
model-authored plan after schema and eligibility validation. Legacy judge,
child-routing, and unit-assignment paths clear unproven specialist identities
instead of restoring confidence, token, ranking, or exact-unit fallbacks.

Exact unit delegation requires inference-authored work-unit claims. Historical
durable plan versions remain replayable without reranking only when the stored
unit IDs and specialist identities still correlate to the same request and
roster. Offline deterministic helpers remain limited to tests and evaluations
and are no longer exported as production workforce entrypoints.

## Challenges encountered

Several mature delegation tests still encoded local lexical assignment as the
expected behavior. The first package run correctly failed seven of them. Those
fixtures were separated into inference-owned assignment tests, fail-closed
tests, and exact durable-replay tests rather than restoring the obsolete
decision path.

## Decisions and alternatives

ADR-0118 governs this boundary. Deterministic recall, host/tool eligibility,
schema validation, compatibility checks, and durable correlation remain valid;
deterministic specialist choice does not. Silently using a local fallback when
inference is absent was rejected because it can present an unreviewed staffing
decision as model-authored evidence.

## Verification

- Focused routing, workforce, hiring, judge, child-routing, unit-assignment,
  delegation, and replay tests: 368 passed, 1 intentional skip.
- Decision conformance: baseline passed; 26 of 26 curated mutations killed;
  zero survivors, zero invalid mutations, and source restoration passed.
- Ruff check, Ruff format, and `git diff --check` passed on the committed tree.
- Immediately preceding telemetry reported 63.2 percent context remaining.

## Follow-ups

Continue AR-204 with exact Codex activation propagation under the documented
autonomous trust bypass, followed by terminal zero-correction header proof.
