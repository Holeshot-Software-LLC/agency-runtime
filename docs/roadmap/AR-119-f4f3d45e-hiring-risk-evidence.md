---
title: "AR-119 Claude technical-diagnosis hiring boundary"
status: active
category: roadmap
created: 2026-08-20
updated: 2026-08-20
tags: [roadmap, evidence, hiring, risk-classification, AR-119, AR-259, AR-261]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/workforce/hiring_contract.py
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 Claude technical-diagnosis hiring boundary

This package records the first ordinary installed-host attempt to hire a
missing specialist after AR-259 and AR-260 reached exact main. It also records
the provider-free classifier reproduction that determines the next bounded
source repair. The live draw was run once and was not retried.

## Exact host draw

- Exact installed source: main `00c4dc7ea901102ff4eab68b7973153e17da46ce`;
  launcher runtime digest `75e998e4af262b857530543c9e20aa4b42d0eab50c307e1619004f4960e794bc`.
- Claude Code session `f4f3d45e-6c83-470e-9f9f-9eafb06c0651`; Agency trace
  `cbaf4f31-fbc3-478b-9072-0dd4016ff27c`; failure receipt
  `ab343cd9-2fc0-4aa6-ac6d-4f5c542c7a4b`.
- The task requested a read-only SAP ABAP/CDS/HANA cardinality diagnosis and
  exactly one native child. Claude exited 0 after two turns without timeout or
  truncation and reported child `ae7446d78801bf83d`.
- The host transcript records zero child tool calls and no file changes. The
  child received only the generic native identity because Agency preflight had
  not produced a staffed route or delivery.
- The host-reported price field was `$0.2808845`; no GitHub-hosted work ran.

## Authoritative terminal evidence

The preflight failure receipt was recorded at
`2026-08-21T02:32:24.619000+00:00` with:

- stage `routing`, reason `substantive_specialist_unavailable`, exception
  category `runtime_error`;
- planner `claude-haiku` / `haiku` applied;
- recruiter `claude-sonnet` / `sonnet` applied;
- staffing reasons `no_safe_sufficient_team` and `recruiter_abstained`;
- hiring reasons `hiring_status_pending_approval` and
  `hiring_inference_attempted`.

The contractor count was 31 before and after. No SAP/ABAP/HANA/CDS contractor,
routing decision, staffed delivery, or correlated hiring case exists. Atomic
preflight therefore preserved Store correctness, but the draw proves neither
staffing nor a genuine hire.

## Evidence limit

AR-259 intentionally retains only the closed hiring status and whether hiring
inference consumed a positive call count. It does not retain the proposed
worker, contract, prompt, response, notification, risk class, or provider
identity. The exact hiring model body is also absent from the deleted private
provider workspace. Consequently, this package does not claim which field or
exact phrase appeared in the generated contract.

## Provider-free classifier reproduction

The exact user task contains the phrase `read-only diagnosis`. The production
contract compiler independently reproduces the defect with a synthetic
SAP-specific contract whose narrow scope is "Read-only diagnosis of ABAP CDS
association cardinality and HANA row duplication": it returns risk class
`medical` and `human_approval_required=true`.

Source inspection explains the result. `classify_contractor_risk` scans every
positive employment-contract field for high-risk markers, and the medical
marker list includes the unqualified word `diagnosis`. The isolated security
review may reason about domain context, but the later deterministic approval
gate does not. The exact generated contract is unavailable, so this is the
unique source-level reproduction consistent with the requested wording and
terminal status, not a claim about unrecoverable model text.

## Next boundary

AR-261 exempts bare diagnosis only when the contract asserts technical context
and no medical context; otherwise it stays owner-gated by default. No second
live draw is admissible until that candidate is
reviewed, locally green, merged, freshly installed, and preceded by telemetry.
No rule or matrix cell moves from this failure.
