---
title: "Worklog detail: Repair critic-rejected contractor proposals"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [workforce, inference, hiring, contractor, reliability]
related:
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
supersedes: []
superseded_by: null
type: worklog
commit: 4fe19c0
short: 4fe19c0
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
---

# Worklog detail: Repair critic-rejected contractor proposals

## Purpose

Repair the exact workforce boundary where a verified gap produced a valid
contractor candidate, the independent critic rejected it with actionable
contract-quality codes, and the two-call hiring budget had no inference-owned
way to produce a safer replacement.

## Approach

Hiring now reserves a four-call maximum for candidate, critique, complete
replacement, and fresh critique. Only the original bounded hiring input and
allowlisted critic reason codes reach the replacement inference; the rejected
candidate is not copied into that prompt and local code never edits its
contract. A repaired candidate passes the same deterministic validation,
duplicate, authority, risk, and atomic-commit boundaries as a first-pass
candidate. Budgets below four stop before an uncriticizable replacement.

## Challenges encountered

The model configured for Agency differed from the parent Codex model, but a
bounded Sol/xhigh comparison reached the same verified-gap/no-contractor shape
as Luna/low. That falsified model choice as the product root cause. The first
implementation also exceeded the repository complexity limit by two branches;
the repair transaction was extracted into a private bounded helper before
checkpoint.

## Decisions and alternatives

ADR-0130 governs the one-replacement limit. Accepting the rejected candidate,
deterministically patching its contract, omitting the second critic, and
retrying until approval were rejected because each weakens inference ownership,
independent review, or bounded cost.

## Verification

- Focused workforce-hiring and configuration tests: 103 passed.
- The success fixture records all four model stages and proves the replacement
  is immediately restaffed without another inference pass.
- Budget exhaustion and second rejection remain content-free and mutation-free.
- Existing first-pass hiring and high-risk approval fixtures remain green.
- Focused Ruff lint and format checks passed; `git diff --check` passed.

## Follow-ups

Run the named fast production spine and decision-conformance evaluation, then
review, merge, and install one exact build. AR-215 remains in progress until one
new activation and one governed product trial prove specialist delegation,
workspace write, a first-pass valid header, zero corrections, and independent
artifact checks.
