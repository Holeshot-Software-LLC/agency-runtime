---
title: "Worklog detail: Record additive promotion evidence"
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
commit: ca48c3fa43e9bd0b2f01cd51df3d50047ceb32ca
short: ca48c3fa
date: 2026-08-25
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/323
related_issues:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
---

# Worklog detail: Record additive promotion evidence

## Purpose

Preserve the exact AR-266 live shadow-value result, the resulting Agency-only
additive promotion, and a changed additive retrieval smoke before publication.

## Approach

Ran the predeclared four-category/four-host evaluator without changing its
targets or thresholds. After all 16 cells passed, backed up the effective
Agency configuration and changed only `workforce.dense_recall_mode` from
`shadow` to `additive`. A new eligible claims-denial work unit then proved that
hybrid recall can append a specialist beyond the retained typed baseline. The
OpenClaw and Hermes native configurations and gateway processes were left
unchanged.

## Challenges encountered

The first broad-spine attempt used an existing Python 3.13 test environment
whose `uv` base interpreter was in a user-replaceable namespace. Seventy-four
persistent-launcher tests correctly failed closed. A changed task-local virtual
environment based on `/usr/bin/python3.12` passed the spine. The first exact
decision-conformance invocation resolved to system Python without `pytest` and
stopped before mutation; a changed task-local executable with the trusted
system fixture interpreter passed the complete evaluation. Neither failure was
retried unchanged.

## Decisions and alternatives

Additive mode was enabled only after the fixed live safety and value gate
passed. The retrieval models remain explicit Agency capability routes; native
host inference, OAuth, and canaries remain outside this package. Directly
editing host configs or making dense evidence a selector was rejected by the
existing AR-266 and ADR-0164 boundaries.

## Verification

- The live matrix passed 16 of 16 cells with 1.0 baseline retention, zero
  category regression, zero forbidden, ineligible, or disabled activation,
  zero provider fallback, safe cache behavior, and one eligible vocabulary gap
  recovered in every host context.
- The changed additive smoke retained the exact 24-card typed prefix and added
  `medical-billing-coding-specialist` to a 26-card recruiter universe.
- 106 focused tests and the named 856-test spine pass with warnings treated as
  errors; 3 spine tests skip.
- All 134 dashboard tests, routing evaluation, and decision conformance with
  160 of 160 mutations killed pass.
- Documentation validation passes for 804 files; full Ruff check and
  format-check and `git diff --check` pass.
- The final SQLite online backup has integrity `ok`, schema 48, and 278 workers.

## Follow-ups

Publish the branch through a reviewed pull request after explicit
authorization. On another machine, run the same fixed live gate while its
Agency configuration remains in `shadow`; enable `additive` there only after a
green local result.
