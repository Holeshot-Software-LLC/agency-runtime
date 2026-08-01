---
title: "Worklog detail: Converge verified contractor gaps"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [workforce, contractors, inference, evidence, product, testing]
related:
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
supersedes: []
superseded_by: null
type: worklog
commit: 4db9c008b8382d4ed32838c0e6270b81d8218cd6
short: 4db9c00
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
---

# Worklog detail: Converge verified contractor gaps

## Purpose

Repair the first boundary exposed by consumed product trial
`ar219-5c45f15-readme-01`. Planner and recruiter inference applied and the
staffing verifier admitted a real gap, but both inference-designed contractor
candidates failed the independent hiring critic before an executable route
could publish.

## Approach

The hiring input now projects bounded, typed work-unit requirements, eligible
coverage, uncovered requirements, and per-worker live ineligibility facts from
the exact staffing context. Both critics receive that evidence, while a single
inference-authored replacement also receives explicit guidance for the three
observed reason families: remove speculative relationships, bind evidence and
evaluations to acceptance checks, and ground the nearest-worker comparison in
the verified projection.

Deterministic code orders and bounds evidence only. It does not rank workers,
select a specialist, synthesize a relationship, edit a candidate, or weaken
the second-rejection terminal boundary.

## Challenges encountered

Atomic failure storage intentionally retained no rejected candidate or private
inferred work unit. The focused fixture therefore preserves the exact product
request and terminal reason family against a representative typed gap without
claiming to reconstruct missing provider content. A review also found that a
missing staffing context could otherwise be misread as positive eligibility;
the projection now marks that state unknown and keeps coverage fail-closed.

An optional broader diagnostic reconfirmed the already-open AR-213 stale-token
fencing defect. It remains outside this bounded hiring package.

## Decisions and alternatives

ADR-0131 records the verifier-evidence boundary. Deterministic specialist
design, accepting the first rejected candidate, removing the critic, retaining
raw recruiter content, and retrying beyond the existing four-call ceiling were
rejected.

## Verification

- Dynamic hiring checks: 37 passed.
- Three new decision mutations: 3 killed, zero survived or invalid, source
  unchanged.
- Focused decision-manifest check, documentation validation, repository-wide
  Ruff lint/format, and `git diff --check` passed.
- Two bounded review passes completed.

## Follow-ups

Run the named local fast gate on the immutable ledger head. If green, review
and merge the repair, install the exact merge, then spend one activation and at
most one product trial before updating the local evidence page and OpenClaw
handoff.
