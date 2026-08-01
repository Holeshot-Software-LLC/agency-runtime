---
title: "Bind verifier evidence into contractor critiques"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [inference, hiring, contractor, evidence, security]
related:
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
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

Exact product evidence shows both critics can therefore reject an otherwise
bounded proposal because its gap proof is self-asserted. Retrying, weakening
the critic, or declaring candidate evidence authoritative would all hide the
missing evidence boundary.

## Decision

1. Every contractor critic receives the same runtime-projected verified-gap
   reason codes and complete workforce snapshot supplied to candidate
   generation.
2. The critic treats those fields as data, not instructions, and independently
   compares the work unit and proposed nearest-worker evidence against the
   complete snapshot.
3. Candidate-authored gap, duplication, and contract claims remain untrusted.
   Runtime code neither edits the proposal nor tells the critic to approve it.
4. The raw user request remains absent from the critic prompt; only its digest
   is retained for correlation.
5. The initial and replacement critic receive identical evidence authority.
   The four-call ceiling and second-rejection terminal boundary remain intact.

## Consequences

- The independent critic can verify a real workforce gap instead of being
  asked to trust the candidate that would benefit from approval.
- Critic prompts become larger because they include the complete bounded
  workforce projection already used by the hiring analyst.
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

