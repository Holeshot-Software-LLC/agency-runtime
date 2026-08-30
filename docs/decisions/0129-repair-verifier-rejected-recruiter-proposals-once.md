---
title: "Repair verifier-rejected recruiter proposals once"
status: accepted
category: decisions
created: 2026-07-31
updated: 2026-07-31
tags: [inference, recruitment, staffing, reliability, diagnostics]
related:
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0129
type: decision
deciders: [maintainers]
---

# ADR-0129: Repair verifier-rejected recruiter proposals once

## Context

The inference stage already permits two semantic attempts per provider. The
recruiter parser validates transport shape and individual nomination structure,
then marks and caches that proposal as applied. Whole-team staffing verification
runs only afterward. A proposal can consequently pass parser acceptance yet
fail composition, assurance, coverage, budget, or deterministic invariant
verification without using the existing repair attempt.

Exact product trial `ar207-e62d0adc-readme-01` demonstrated that boundary. Its
planner and recruiter receipts were applied, but preflight retained no route.
The exact same prompt immediately produced an accepted eight-unit team through
the read-only route surface, proving that neither the roster nor host eligibility
was the limiting condition.

## Decision

1. Treat full `verify_staffing` acceptance as part of recruiter-stage semantic
   acceptance. A verifier-rejected proposal raises a bounded validation result
   inside the existing provider attempt and receives at most the one already
   authorized semantic repair call.
2. Do not cache, project, or label a recruiter proposal applied until full
   staffing verification accepts it or it is a valid explicit inferred-gap
   proposal eligible for governed contractor hiring.
3. Preserve inference authority. The verifier may reject and provide typed
   reason codes, but it may not synthesize, rank, or select a replacement team.
4. Exhausted repair, unavailable budget, and a second invalid proposal remain
   terminal for substantive turns. There is no resident or parent-generalist
   fallback.
5. Project bounded verifier abstention and hiring reason codes into terminal
   preflight evidence. Continue excluding prompts, responses, free-form model
   rationale, exceptions, paths, credentials, and raw process output.

## Consequences

- A transient, structurally valid but non-executable recruiter sample can use
  the call already reserved for semantic repair instead of failing immediately.
- Total calls remain bounded by the existing workforce mode budget; this
  decision adds no retry loop and no new provider authority.
- Explicit model-declared gaps continue through contractor hiring. Local code
  still cannot transform an ordinary rejection into a semantic gap or team.
- Failure evidence becomes actionable without exposing model or user content.

## Alternatives

- **Accept the first structurally valid proposal.** Rejected because transport
  validity is not executable staffing evidence.
- **Construct the verifier's deterministic minimum as the team.** Rejected
  because that silently restores deterministic selection and violates
  inference ownership.
- **Retry until some team passes.** Rejected because it is unbounded, costly,
  and biases evidence toward eventual success.
- **Fail without reason projection.** Rejected because it recreates the
  multi-hour diagnosis this bounded evidence contract is meant to prevent.
