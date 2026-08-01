---
title: "Repair critic-rejected contractor proposals once"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [inference, hiring, contractor, reliability, security]
related:
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0130
type: decision
deciders: [maintainers]
---

# ADR-0130: Repair critic-rejected contractor proposals once

## Context

Agency's open-ended workforce contract requires inference to design a narrow
specialist when a recruiter-declared gap survives deterministic verification.
The hiring path currently spends one call on the candidate contract and one on
an independent safety critic. A critic rejection is terminal even when its
bounded reason codes identify correctable contract defects. Exact product and
read-only routing evidence show this can leave a valid multi-unit request with
no specialist despite a proven gap and available inference.

Accepting the rejected candidate would weaken the security boundary. Having
deterministic code edit or synthesize its contract would violate inference
ownership. Repeating until approval would be unbounded and would bias evidence
toward eventual success.

## Decision

1. A deterministically valid candidate rejected by the independent critic may
   receive exactly one inference-authored replacement attempt.
2. The replacement prompt contains the original bounded hiring input plus only
   allowlisted critic reason codes and a requirement for a complete replacement
   contract. It does not treat the critic as selection authority or let local
   code edit the candidate.
3. A fresh stateless critic must independently approve the replacement before
   it can be compiled, staged, applied, or used for restaffing.
4. The sequence is bounded to four calls: candidate, critic, replacement,
   critic. A configured budget below four preserves the existing terminal
   rejection and never starts a replacement it cannot independently critique.
5. Provider failure, invalid replacement, second rejection, high-risk approval,
   duplicate detection, and all existing deterministic safeguards remain
   fail-closed. Deferred preflight remains the only ordinary task commit path.

## Consequences

- Correctable critic findings can converge without turning the parent into a
  generalist or letting deterministic code choose a worker.
- A gap can cost two additional provider calls and latency. The default hiring
  budget increases from two to four while the per-task and per-day workforce
  mutation limits remain unchanged.
- Two independent rejection outcomes remain terminal. The product contract
  still values safety over guaranteed eventual success.
- Model and reason-code receipts cover the complete bounded sequence without
  retaining prompts or candidate content in durable failure evidence.

## Alternatives

- **Apply the first candidate despite critic rejection.** Rejected because the
  critic is the independent safety boundary.
- **Patch the contract deterministically.** Rejected because it restores a
  hidden deterministic specialist designer.
- **Skip the second critique.** Rejected because repaired content is a new
  untrusted candidate.
- **Retry until approved.** Rejected because cost, latency, and selection bias
  become unbounded.
- **Treat every rejection as final.** Rejected because it makes the advertised
  open-ended contractor pool brittle to one correctable inference sample.
