---
title: "Worklog detail: Preserve planner repair diagnostics"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [inference, planning, observability, repair]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
supersedes: []
superseded_by: null
type: worklog
commit: 4bd18867daeef973ba0dc1e51a7eb5abc76f1710
short: 4bd18867
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-275-preserve-planner-repair-diagnostics.md
---

# Worklog detail: Preserve planner repair diagnostics

## Purpose

Make strict planner failures diagnosable without another provider call and make
the one existing repair attempt easier for any model behind an opaque profile
or LiteLLM alias to satisfy.

## Approach

Added a bounded validation-code tuple to planner inference attempts, preserved
it through routing, and projected it into terminal preflight receipts only
after complete closed-vocabulary validation. Exact plan-policy codes survive;
other deterministic planner semantic failures use one fixed generic code.
The existing single repair call now uses a concise compact-plan repair system
contract while strict local parsing, budgets, fallback policy, and alias
opacity remain unchanged.

## Challenges encountered

Expected-red produced four exact failures. One broader affected run inherited
umask `0002`, causing 29 trusted-temp Store failures, and exposed one stale
test assertion for the intentionally changed repair system. Process-local
umask `0077` plus the corrected assertion passed 178 tests with one skip.
Decision conformance could not start mutations because its trusted isolated
fixture resolves to `/usr/bin/python3.12`, where pytest is unavailable.

## Decisions and alternatives

Structured runtime-owned codes were chosen over parsing or persisting generic
validation prose. A dedicated repair contract was chosen over model-specific
prompt branches, alias inspection, more retries, relaxed validation, or a
protected-provider fallback. ADR-0027 and ADR-0164 govern those boundaries.

## Verification

Expected-red: 4 failed, 4 passed. Repaired focused: 8 passed. Affected slice:
178 passed, 1 skipped. Named production spine: 827 passed, 3 skipped. Full
ruff check/format, docs metadata/policy/worklog/docs verification, 134 UI
tests, routing evaluation, and diff checks passed. Decision conformance is
retained as a launcher limitation, not a pass.

## Follow-ups

Install Agency only into stopped OpenClaw from this checkpoint and run one
genuinely new substantive turn. Tracker creation remains separately
unauthorized under AR-275.
