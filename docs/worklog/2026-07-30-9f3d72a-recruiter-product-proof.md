---
title: "Worklog detail: Converge recruiter and product proof"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [workforce, inference, recruiter, product-evaluation, codex, mutation-testing]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/decisions/0115-aggregate-bounded-recruiter-repair-failures.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 9f3d72a
short: 9f3d72a
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
---

# Worklog detail: Converge recruiter and product proof

## Purpose

Repair the two first-class defects exposed by terminal trial
`ar201-ed4450e-ordinary-01`: one bounded recruiter repair could not converge
across multiple invalid units, and the product harness neither consumed the
exact activation snapshot nor proved effective model-facing workspace writes.

## Approach

Recruiter validation now aggregates an ordered allowlisted failure set for all
planned units. A same-provider accumulator discards failed rows, retains valid
rows, accepts a partial repair, and reconstructs the proposal in exact plan
order without selecting candidates deterministically.

The Codex product backend now projects one exact trusted workspace only into
its disposable profile. The same model invocation must create a prompt-bound
sentinel under the retained workspace-write sandbox. Product grading fails
closed unless exact-workspace trust and the sentinel are proven. Agency mode
queries the Store's exact activation snapshot for the wrapped prompt actually
executed while preserving the canonical product prompt hash separately.

## Challenges encountered

The first mutation-gate rerun stopped at its baseline because the newly selected
product one-shot test imported a support fixture that the isolated evaluator
did not copy. No mutation ran and source fingerprints remained unchanged. The
fixture was added to the evaluator's explicit copied support set; the next
baseline passed and all 13 mutations were killed.

Review also found that a missing `workspace_write_proven` value would retain a
legacy path into product grading. The boundary now requires exact `True`, and
the null case has its own decision-conformance mutation.

## Decisions and alternatives

[ADR-0115](../decisions/0115-aggregate-bounded-recruiter-repair-failures.md)
keeps online selection inference-owned while making one bounded repair
convergent. [ADR-0116](../decisions/0116-bind-product-trials-to-exact-workspace-proof.md)
keeps persistent trust outside the trial, rejects requested flags as sufficient
proof, and binds activation and write evidence to the exact execution.

## Verification

- Focused and adjacent runtime suite: 85 passed.
- Decision conformance: green baseline; 13/13 mutations killed; zero survivors
  or invalid results; source inputs unchanged.
- Full Ruff lint passed; 603 files were format-clean.
- Documentation metadata, policy availability, worklog-currentness, and normal
  validation passed for 548 Markdown files.
- Git diff checks passed.

## Follow-ups

Run the named fast production spine, push and merge the PR, install the exact
merged revision for Codex and ZCode only, then spend one final ordinary product
canary and publish its local evidence report.
