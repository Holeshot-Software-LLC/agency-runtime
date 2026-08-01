---
title: "Compile contractors from governed structured contracts"
status: accepted
category: decisions
created: 2026-07-21
updated: 2026-08-01
tags: [contractors, hiring, security, roster]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
supersedes: []
superseded_by: null
id: ADR-0081
type: decision
deciders: [maintainers]
---

# ADR-0081: Compile contractors from governed structured contracts

## Context

Real capability gaps must be fillable in the same task, but unrestricted
model-authored prompts would create prompt-injection, authority, duplication,
portability, and roster-bloat risks.

## Decision

Contractor creation is available only with configured inference and a durable
gap proof against every workforce state. The recruiter must explicitly declare
the unit a gap, the staffing verifier must confirm the exact safe no-team reason
closure, and the hiring analyst must independently compare the need against the
complete workforce. A recruiter staffing failure is not itself a gap.

Inference emits a bounded structured employment contract; Agency compiles it
through a fixed reviewed template and an independent critic validates safety
and differentiation. Inference chooses the coherent amendment target; that
existing worker then owns the revision's identity, authority, and context
boundary. Additive projections preserve every existing value before accepting
new values within the destination schema. Distinct gaps create stable
contractor identities. `max_hires_per_task` counts applied workforce changes,
not declined analyses, so one disputed gap cannot consume the allowance needed
by a later proven gap. Every lifecycle transition preserves versions, evidence,
and superseding links.

## Consequences

Agency can hire and use a narrow specialist immediately without executing
untrusted system instructions. The workflow needs duplicate analysis, hiring
budgets, high-risk human approval, performance evidence, expiration review, and
operator lifecycle controls.

## Alternatives

Executing generated prompts directly was rejected as unsafe. Never hiring was
rejected because genuine gaps would remain uncovered. Automatically extending
the nearest worker was rejected because it would create incoherent super-agents.
