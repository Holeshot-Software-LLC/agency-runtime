---
title: "AR-432: Preserve numeric facts in review plans"
status: open
category: roadmap
created: 2026-09-10
updated: 2026-09-10
tags: [planning, reliability, evidence]
related:
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/worklog/2026-09-10-hermes-assurance-investigation.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-432
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/845
depends_on: []
blocks: []
---

# AR-432: Preserve numeric facts in review plans

## Problem

The accepted plan for a supplied numeric review says the arithmetic mean of
`[1.0, 2.0]` should be `2.5`. The correct value is `1.5`. This contradicts the
requested arithmetic-mean semantics and could misdirect downstream work.

## Current state

Fresh Hermes session20260910_081128_6d1bcd, trace ending df76d074, has the bad
fact in unit-defect-analysis of plan910281981fa6. Both recruiter and critic
packets preserve it. The staffing critic approved the two-unit plan and the
native answer correctly used1.5; all native card/header/terminal gates passed.
No bad user-visible arithmetic answer or historical critic defect is claimed.
See evidence/AR-404-assurance-native-recruiter-20260910.json and
AR-404-assurance-native-critic-20260910.json, native_packet.original_input.plan,
and the native summary/response beside them. The raw planner transport response
was not captured, so its model-versus-normalization origin remains unresolved.
This is a deferred finding from PR844, not a repair in that evidence package.

## Approach

Trace where the false expected value entered the plan. Preserve supplied
examples and requirements through inference-owned planning; choose a bounded
repair only after identifying that boundary. Do not turn staffing selection
into numeric heuristics or assume its pre-execution critic verifies answer
arithmetic. Retain the independent critic, validators, trust and failed receipts.

## Dependencies

AR-404 reliability evidence; ADR-0200 keeps staffing assurance separate from
completed-task correctness. AR-418 truncation remains a separate issue.

## Acceptance

- [ ] Reproduce and locate the incorrect numeric statement at its actual
      planner or normalization boundary, retaining the exact input and output.
- [ ] Preserve supplied examples without changing inference-only staffing,
      critic remit, validator or trust boundaries; demonstrate a negative control.
- [ ] Run focused/required fast checks and one bounded fresh native diagnostic,
      with criterion evidence, isolated verdicts and tracker/worklog parity.
