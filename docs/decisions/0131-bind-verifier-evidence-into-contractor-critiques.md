---
title: "Bind verifier evidence into contractor critiques"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [inference, hiring, contractor, evidence, security]
related:
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/issue-AR-220-converge-product-recruiter-evidence.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0131
type: decision
deciders: [maintainers]
---

# ADR-0131: Bind verifier evidence into contractor critiques

## Context

ADR-0130 requires a fresh independent critic for both an original contractor
candidate and its only allowed replacement. The hiring analyst sees the exact
work unit, a bounded upstream verified-gap projection, and the complete
workforce. The critic sees only candidate-authored gap evidence, the candidate
contract, and fixed compiler hashes. Its instruction correctly says that this
material is untrusted, but it has no independent source with which to confirm
the gap or nearest-worker comparison.

Exact product evidence first showed critics rejecting an otherwise bounded
proposal because its gap proof was self-asserted. A later product trial proved
that reason codes plus the complete workforce are still insufficient when the
critic must reconstruct typed requirements, live eligibility exclusions, and
uncovered coverage from raw contracts. Retrying, weakening the critic, or
declaring candidate evidence authoritative would all hide the missing evidence
boundary.

## Decision

1. Every contractor critic receives the same runtime-projected verified-gap
   reason codes and complete workforce snapshot supplied to candidate
   generation.
2. The projection also carries typed work-unit requirements, eligible coverage,
   uncovered requirements, and bounded per-worker coverage plus live
   ineligibility reasons from the exact staffing context. Missing context is
   labeled unknown and never interpreted as eligibility.
3. This projection is evidence only. Deterministic code may order and bound
   rows for transport, but it does not rank workers, select a specialist, edit
   a contract, or tell the critic to approve it.
4. A single inference-authored replacement receives the original verified-gap
   projection and bounded critic reason families so it can remove speculative
   relationships, bind evaluations to acceptance checks, and make the
   nearest-worker insufficiency concrete.
5. Candidate-authored gap, duplication, and contract claims remain untrusted.
   The raw user request remains absent from critic prompts; only its digest is
   retained for correlation.
6. The initial and replacement critic receive identical evidence authority.
   The four-call ceiling and second-rejection terminal boundary remain intact.

## Consequences

- The independent critic can verify a real workforce gap instead of being
  asked to trust the candidate that would benefit from approval.
- A replacement remains inference-designed but receives enough typed evidence
  to answer relationship, acceptance, and independent-gap findings once.
- Critic prompts become larger because they include the complete bounded
  workforce projection already used by the hiring analyst plus bounded typed
  coverage rows.
- A worker that actually covers the unit remains visible to the critic, while
  disabled-worker and deterministic duplicate checks still fail before commit.
- Live success still requires a fresh exact build; the consumed failed trial
  cannot be reinterpreted or rerun.

## Alternatives

- **Tell the critic that candidate gap evidence is trustworthy.** Rejected
  because the candidate cannot independently validate itself.
- **Remove gap validation from the critic.** Rejected because duplicate and
  roster-bloat protection requires an independent workforce comparison.
- **Pass the raw user request as critic authority.** Rejected because user
  content is untrusted and the work unit already carries the bounded outcome.
- **Keep retrying candidates.** Rejected because it is unbounded and does not
  repair the missing evidence source.
