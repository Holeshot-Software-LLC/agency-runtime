---
title: "Worklog detail: Bind gap evidence into contractor critics"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [workforce, inference, hiring, contractor, evidence]
related:
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-216-preserve-required-product-scenario-files.md
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
supersedes: []
superseded_by: null
type: worklog
commit: aaf80f7
short: aaf80f7
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-216-preserve-required-product-scenario-files.md
---

# Worklog detail: Bind gap evidence into contractor critics

## Purpose

Repair the exact product boundary where both bounded contractor critics had
only candidate-authored gap evidence to distrust. The consumed live trial
therefore stopped before route commit, specialist delegation, header creation,
or workspace write even though planner and recruiter inference both applied.

## Approach

Both the original and replacement critic prompts now receive a
`runtime_gap_evidence` projection containing the upstream verified-gap codes,
workforce count, and exact complete workforce snapshot already used by hiring.
Candidate gap, duplicate, and contract claims remain untrusted. The raw request
stays out of critic authority, local code does not design or approve a worker,
and the four-call/second-rejection boundary is unchanged.

The same checkpoint also records, without implementing, the separate PR 213
P1 finding that product resource extraction can omit explicit required files.
AR-216 owns that bounded follow-up.

## Challenges encountered

The exact `9c2e9f8` product trial was single-use and terminal. Durable failure
evidence retained only content-free reason codes, so the implementation was
derived by correlating those codes with the only terminal path that returns
them and reviewing the exact critic prompt boundary. No retry or additional
provider diagnostic was used.

## Decisions and alternatives

ADR-0131 governs the evidence handoff. Trusting candidate-authored evidence,
removing critic gap validation, passing the raw request as authority, and
retrying until approval were rejected because each weakens independent review,
prompt isolation, or bounded execution.

## Verification

- Evidence-sensitive hiring suite: 32 passed.
- Broader workforce/routing set: 121 passed, 1 skipped.
- Named Python production spine: 643 passed, 6 skipped.
- Dashboard UI: 110 passed.
- Documentation: 608 Markdown files validated.
- Routing evaluation: every correctness, performance, scale, and startup gate
  passed.
- Decision conformance: baseline passed; 73/73 mutations killed, zero survived
  or invalid, and `source_unchanged=true`.
- Repository-wide Ruff lint/format and `git diff --check` passed.

## Follow-ups

Review and merge one exact PR, install that merge, and run one activation plus
at most one fresh product trial. AR-217 remains in progress until the product
trial proves specialist delegation, workspace write, a first-pass valid
header, zero corrections, and independent artifact validation. AR-216 remains
the separate all-scenario resource-scope follow-up.

