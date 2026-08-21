---
title: "AR-261: Disambiguate technical diagnosis from medical authority"
status: in_progress
category: roadmap
created: 2026-08-20
updated: 2026-08-21
tags: [hiring, security, risk-classification, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/roadmap/AR-119-f4f3d45e-hiring-risk-evidence.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/workforce/hiring_contract.py
  - tests/test_workforce_hiring_contract.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-261
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/309
depends_on: [AR-259]
blocks: [AR-119]
---

# AR-261: Disambiguate technical diagnosis from medical authority

## Problem

The deterministic contractor risk classifier treats the bare word `diagnosis`
as medical authority in every domain. An ordinary technical employment
contract such as "Read-only diagnosis of ABAP CDS association cardinality"
therefore receives the `medical` risk class and requires owner approval. In an
atomic host preflight, that valid approval-required proposal is rolled back
when restaffing cannot continue, so the workforce remains unchanged and the
operator has no case to approve.

## Current state

- Exact-main Claude session `f4f3d45e-...` ended with terminal receipt codes
  `hiring_status_pending_approval` and `hiring_inference_attempted`; the Store
  has zero correlated hiring cases and the workforce stayed at 31 contractors.
- A provider-free source reproduction classifies an SAP-specific technical
  diagnosis contract as `medical` with `human_approval_required=true`.
- Raw hiring responses are intentionally not retained, so the exact generated
  contract and its triggering field cannot be claimed.
- Tracker [#309](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/309)
  is open with the required `epic:security` label.

## Approach

Keep the mandatory isolated security review and every unambiguous high-risk
marker unchanged. Bare `diagnosis` remains owner-gated by default. Exempt it
only when the contract asserts bounded technical context such as software,
database, runtime, SAP, ABAP, HANA, CDS, or SQL and asserts no medical context.
Context may be in a different contract field. A medical, clinical, or patient
role with a `diagnosis` capability, and an otherwise context-free diagnosis,
remain owner-gated. Explicit prohibitions continue to be ignored as grants.

## Dependencies

- AR-259 supplies the content-free terminal evidence that made this boundary
  diagnosable without retaining provider content.
- AR-122 owns governed contractor compilation and approval.
- The independent security reviewer remains the inference-owned safety gate;
  this change only narrows deterministic owner-approval classification for an
  overloaded word.

## Acceptance

- [x] A technical SAP/database diagnosis contract is standard risk.
- [x] Medical diagnosis in one field remains owner-gated.
- [x] A clinical or patient role plus a separate diagnosis capability remains
      owner-gated.
- [x] Existing explicit-prohibition and other high-risk-marker tests remain
      green.
- [x] The focused hiring suite passes 88/88 and all 12 proportional local
      gates pass in 1.3 minutes on the exact candidate.
- [x] Tracker issue #309 is created after explicit authorization.
- [ ] The candidate is published through a reviewed PR with no hosted work.
- [ ] One later authorized exact-main draw proves a genuine hire; no retry of
      session `f4f3d45e-...` is permitted.
