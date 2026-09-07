---
title: "Reconcile CodeQL measurement and legacy tracker gates"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [ci, security, evidence, cost, backlog]
related:
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
  - docs/roadmap/acceptance/evidence/AR-162-record-reconciliation-20260907.md
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0226
type: decision
deciders: [maintainers]
---

# ADR-0226: Reconcile CodeQL measurement and legacy tracker gates

## Context

Implementation and initial evidence are committed at fcdcd6eb; the roadmap and
worklog registry preserve its exact subject and bounded verification.

AR-162's eighth criterion asks for a matched hosted unavailable-path topology
and duration record before accepting speed or billing savings. Its original
private-repository scenario no longer describes this repository: September 7
read-only identity reports public/non-fork, and the authenticated code-scanning
endpoint returns HTTP 200 with an alert array. This proves availability only
for that calling identity, not a workflow-token or current analyzer pass.

The owner requested relevance-led reconciliation of agent-written requirements.
The one-preflight/conditional-matrix/stable-aggregate implementation can be
verified without manufacturing an unlicensed private repository or changing
hosted entitlements. Historical 0.34/0.24 raw runner-minutes are not a current
comparison or GitHub billing units. No savings are claimed.

First review c456b6bd accepted criteria 1–6 and 8 but found missing historical
comparison evidence for 7 and missing remote parity for 9. AR-347 already
established a versioned pre-tracker exemption, explicitly including AR-162.
Creating a redundant tracker to satisfy older wording would contradict that
owner-approved reconciliation. Preserve the failed first verdicts and adopt the
existing rule explicitly; do not reinterpret them as satisfied old criteria.

## Decision

Retain the explicitly revised eighth criterion:

"Current hosted capability and check-evidence limits are reported accurately;
any speed or billing-savings claim requires a matched hosted unavailable-path
topology and raw-duration measurement, and no such claim is made without it."

Following the preserved first review, replace the ninth criterion with:

"AR-162 follows the governed pre-tracker exemption while unmapped; both strict
documentation/tracker checks pass, and any later authorized tracker mapping has
exact URL/state parity with the local record."

Preserve both original wordings and old telemetry. Criteria 1–7 remain unchanged;
add the missing historical comparison for 7. Require all nine isolated verdicts
at a new candidate before completion. The eighth-criterion revision separates
functional correctness from an optional, claim-triggered cost measurement;
it does not call an unperformed benchmark passed.

Keep exact fail-closed capability handling, both available language analyses,
permissions, events, aggregate checks and unavailable evidence. AR-159 still
owns current successful check identities and hosted branch enforcement. Its
open state and authority requirements are unaffected. No setting, workflow
dispatch, subscription or native CodeQL analysis is authorized here.

## Consequences

- Implementation completion cannot be presented as hosted CI success or savings.
- A future savings assertion still needs a matched run and a correct distinction
  between raw durations and provider billing; the condition is not discarded.
- Missing current hosted checks remains explicit under AR-159; the endpoint
  read cannot satisfy that record or establish workflow-token authority.
- ADR-0037 and ADR-0097 remain accepted and unchanged.
- AR-347's self-shrinking exemption is unchanged: once mapped, the ID must leave
  the exemption list and both strict checks enforce ordinary URL/state parity.

## Alternatives

- Recreate the private/unlicensed scenario as a mandatory completion gate:
  rejected because no current cost claim needs it and it requires external
  resources or authority outside this slice.
- Declare the old benchmark satisfied from local tests or job count: rejected.
- Remove the unavailable path or security analysis: rejected; both configured
  paths and their fail-closed guarantees remain required.
- Create a duplicate legacy tracker or silently call old parity satisfied:
  rejected in favor of explicitly applying the existing governed exemption.
