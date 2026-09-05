---
title: "Retire the superseded live-routing contract without claiming live success"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [routing, evidence, backlog, supersession]
related:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-357-canonical-response-contract-statement.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - agency_runtime/core/header/contract.py
  - agency_runtime/core/header/response_contract.py
  - tests/test_routing_correctness.py
  - tests/test_response_contract.py
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0078-present-human-routing-evidence-and-abstain-on-noise.md
superseded_by: null
id: ADR-0222
type: decision
deciders: [maintainers]
---

# ADR-0222: Retire the superseded live-routing contract without claiming live success

## Context

The owner requested oldest-first, one-item-at-a-time backlog reconciliation,
judging old agent-authored requirements against the product now wanted.
AR-115 is the oldest unfinished record at e5662d91. Its installed tests remain
unproven, but its six-line Why/How header, optional inference and strong-signal
heuristic specialist fallback are no longer the supported product contract.
ADR-0078 remained accepted even after those decisions changed.

ADR-0118 already prohibits deterministic specialist selection. The implemented
AR-357 contract derives exactly five header fields from HEADER_FIELDS and
distinguishes unreadable evidence from missing user-response requirements.
Its completed implementation explicitly removed the stale seven-line promise.
AR-119 owns the current vision-rule/host evidence matrix; AR-125 owns the
configured/held-out selection and paired outcome evidence. Neither is complete.

## Decision

Retire AR-115 as wont_do, superseded by AR-119, not as successfully verified.
Replace ADR-0078 with these existing current authorities:

| Retired contract | Current authority and retained responsibility |
|---|---|
| Heuristic fallback chooses compatible specialists without inference | ADR-0118: inference chooses or selection fails loudly with no specialist; recall and hard validation remain deterministic. |
| Six-field header containing Why/How, or another historical fixed count | AR-357 and HEADER_FIELDS: five current-turn evidence fields. ADR-0120's first-publication evidence principle remains; historical field counts do not override the implemented canonical contract. |
| A configured-inference and heuristic-selection installed matrix closes AR-115 | AR-119/AR-125 retain ordinary configured staffing, truthful abstention/failure, forbidden-selection and exact-host evidence. No second competing legacy completion matrix is maintained. |
| Every small delivery requires the full corpus and hosted CI | ADR-0105 and AGENTS.md: focused checks and named fast spine; exhaustive integration is separately authorized. Exact live evidence still applies to a live claim. |

Retain machine-readable routing diagnostics and human-readable explanations on
their current diagnostic surfaces. Do not restore Why/How fields, use resident
managers as an unrecorded specialist fallback, weaken confidence/eligibility
checks, or normalize new host identities merely to make an old checkbox pass.
The old implementation narrative and checked/unchecked acceptance remain
explicit historical evidence in AR-115.

AR-119 absorbs the still-relevant live-selection/header outcome and no longer
depends on successful completion of the retired AR-115 design. AR-125 retains
the independent evaluation responsibility. Current credential-unset and
unverified-header observations are unresolved operational failures, not proof
of completion and not erased by retirement. The owner has explicitly chosen
backlog reconciliation before that live-session diagnosis.

## Consequences

- One contradictory legacy proposal leaves the open queue, but the actual
  live problem remains owned and visible in the current umbrella/evaluation.
- No runtime, tests, configuration, credentials, host trust or lifecycle state
  change. Current-source regression checks can verify this accounting boundary;
  they cannot certify staffing quality or ordinary native sessions.
- AR-115 is closed as not planned/superseded. No acceptance verdict is fabricated
  for its three historically unproven gates.

## Alternatives

- **Mark AR-115 done because tests pass.** Rejected: its original installed
  matrix never received proof, and this session remains unstaffed/unverified.
- **Reimplement its original fallback and header design.** Rejected: conflicts
  with inference-owned staffing and the canonical response contract.
- **Keep both live umbrellas open indefinitely.** Rejected: duplicate,
  contradictory completion plans obscure the actual unresolved outcome.

## Verification basis

The review uses source and records at e5662d91, including the historical AR-256
reopening note. Focused routing/header/credential/resident-manager and document/
tracker checks pass 183 tests in 19.11s. They include strong lexical matches
without inference selecting nobody, no policy repopulation after failure, the
canonical response text, and unreadable-evidence handling. No live pass is
claimed. Exact current proof limitations remain in AR-119 and AR-125.
