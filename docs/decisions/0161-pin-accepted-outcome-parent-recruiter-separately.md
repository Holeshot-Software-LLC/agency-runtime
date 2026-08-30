---
title: "Pin the accepted-outcome parent recruiter separately"
status: accepted
category: decisions
created: 2026-08-20
updated: 2026-08-20
tags: [canary, inference, providers, workforce, outcomes, security]
related:
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/canary_parent_recruiter_provider.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/workforce/inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0161
type: decision
deciders: [lkrammes]
---

# ADR-0161: Pin the accepted-outcome parent recruiter separately

## Context

The first exact-main Claude accepted-outcome draw failed before planning. PR
#302 made the canary's parent request explicitly indivisible, and the next
authorized draw live-proved that repair: the configured Haiku planner returned
one valid work unit. The configured Sonnet recruiter then returned
`staff_without_safe_team` for four implementation candidates, and its funded
repair produced no valid response. No route, child-judge call, outcome, or
promotion followed.

The same repository already has successful Codex-subscription planner and
recruiter receipts, while the instrument series records intermittent structured
contract failures on the Claude/Sonnet recruiter. Retrying the unchanged route
would spend another provider draw without isolating a variable. Changing the
Claude harness route would also alter real turns, which the owner did not
authorize.

The accepted-outcome parent recruiter and the native child judge are different
inference roles. ADR-0160's map authorizes only child staffing after a native
launch reaches the Agency hook; it cannot silently become authority for parent
preflight.

## Decision

Agency configuration owns a distinct
`canary.accepted_outcome_parent_recruiter_provider_by_host` map. The current
Claude accepted-outcome proof configuration names `codex-subscription`. No
value ships by default and installing Agency does not mutate the owner's map.

Canary preparation resolves the active host's value to exactly one configured
Codex or Claude CLI provider. Missing, ambiguous, unsupported, or mismatched
identity fails closed. The disposable accepted-outcome backend projects that
provider name through
`AGENCY_ACCEPTED_OUTCOME_PARENT_RECRUITER_PROVIDER` and copies only the bounded
CLI authentication file required by a cross-provider transport into its private
runtime home.

Workforce inference consumes the projection only when all of these are true:

- `AGENCY_CANARY_MODE=1`;
- the dedicated accepted-outcome parent-recruiter projection is nonempty;
- the stage is the primary `recruiter`; and
- the route key is exactly `workforce.recruiter`.

The initial recruiter call and its one funded repair share the resulting
one-provider tuple with no fallback. The parent planner, recruiter critic,
hiring stages, ordinary host turns, and other canary modes continue through
their existing profile routes. Native child staffing continues through the
independent `canary.child_judge_provider_by_host` authority.

Reports retain the requested parent-recruiter and child-judge identities as
separate fields. The requested value is not proof that a provider answered;
actual provider attribution continues to come from the corresponding inference
attempt or model receipt.

## Consequences

- The accepted-outcome canary can isolate the measured recruiter variable
  without changing the host driving the parent session or any general-turn
  route.
- Activation canaries remain byte-for-byte on their configured recruiter path
  because they never receive the dedicated environment projection.
- Parent recruiter and child judge policy can differ without either role
  inheriting the other's authority.
- Cross-provider proof uses another disposable credential copy, but no owner
  credential path or secret enters reports or the Store.
- A source change alone proves no provider response, accepted outcome,
  promotion, or AR-119 matrix cell. Publication, owner configuration,
  exact-main installation, and a bounded live draw remain separate gates.

## Alternatives

- **Retry Claude/Sonnet unchanged.** Rejected because the consumed draw already
  reproduced the documented intermittent recruiter failure and a retry would
  not isolate a new variable.
- **Change `inference.harnesses.claude.routes.workforce.recruiter`.** Rejected
  because that changes real Claude turns outside the canary authorization.
- **Reuse the child-judge map.** Rejected because parent preflight and native
  child staffing are separate roles reached at different lifecycle boundaries.
- **Hard-code `codex-fast` or a workstation profile name.** Rejected because
  profile aliases are owner-specific; the explicit configured provider is the
  portable evidence identity.

## Provenance

The exact draw, Store correlation, and no-matrix-movement boundary are recorded
in the AR-119 loop status and AR-252 issue. This decision records the owner's
2026-08-20 local implementation choice; it does not authorize publication,
configuration mutation, installation, or another provider call.
