---
title: "Fail open with an honest header when no specialist is selected"
status: accepted
category: decisions
created: 2026-08-03
updated: 2026-08-03
tags: [orchestration, inference, failure, header, product]
related:
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - README.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
superseded_by: null
id: ADR-0152
type: decision
deciders: [maintainers]
---

# ADR-0152: Fail open with an honest header when no specialist is selected

## Context

ADR-0122 mandated that a substantive turn with no accepted specialist must block
the parent model terminally ("resident-only completion cannot turn the parent
model into a generalist; substantive work is specialist-staffed or terminally
unavailable"). The intent was honesty: never let a generalist answer be
mislabeled as specialist work.

In practice that boundary bricked the host. Any staffing hiccup — a transient
provider timeout, an over-conservative plan-policy veto, a recruiter abstention,
or a verifier rejection — produced a `decision: block` on `UserPromptSubmit`
that locked the operator out of the main agent entirely. The block message
("Restore inference or staffing") pointed at inference even when the provider
was configured and successfully called, because the real reason (recruiter
abstention, plan-policy veto, etc.) was discarded before the message was
composed. With the full planner → recruiter → gap → contractor-hiring pipeline
in place, a real specialist should handle nearly every substantive turn, so a
generalist fallback would rarely fire; when it does, an operator prefers a
generalist answer over being unable to communicate with the agent at all.

The honesty goal does not require a block. Agency already stamps a
machine-authored `Recruited via` header line (`inference`, `cached`, or `none`)
that is independent of the model-authored `Why`. A fail-open turn can carry
`Recruited via: none` so a generalist answer is never mislabeled as specialist
work, while the persisted failure receipt keeps the dashboard and logs
diagnosable with the exact cause.

## Decision

When a substantive turn cannot produce an accepted specialist (provider failure
or unavailability, recruiter abstention, plan-policy veto, verifier rejection,
or an unresolvable plan), Agency **fails open**: the parent model answers as a
generalist and the response carries an honest `Recruited via: none` header.

1. `_require_substantive_specialist` raises `SubstantiveSpecialistUnavailable`
   carrying the exact persisted cause (`status`, `source`, `inference_mode`, and
   the joined `error`/`inference_failures` reason codes).
2. `run_preflight` catches that exception, persists the failure receipt (so the
   dashboard and logs stay diagnosable), and returns an honest zero-specialist
   `PreflightResult` instead of re-raising.
3. The response header stamps `Recruited via: none` so the generalist answer is
   never mislabeled as specialist work.
4. The CLI surfaces the exact `status`, `error`, and `inference_failures` so
   `agency route "<prompt>"` is immediately diagnostic.

The hard block remains for **non-staffing integrity failures** (evidence-store,
lifecycle, reservation, or assignment corruption). Those `RuntimeError`s still
produce `decision: block`, now with the exact cause appended. Staffing
availability is not an integrity failure.

This partially supersedes ADR-0122's "fails before accepting a domain answer"
and "terminally unavailable" passages. ADR-0122's core decision — one
Agency-native parent-only `agency-steward`, inference owns staffing, no
deterministic no-match fallback worker — stands unchanged.

## Consequences

- An operator is never locked out of the host by a staffing hiccup; the main
  agent always answers.
- A generalist answer is always honestly labeled (`Recruited via: none`); it is
  never mislabeled as specialist work.
- The exact failure cause is persisted in the receipt and surfaced in the header
  and CLI, so the operator can diagnose and fix the real provider, verifier, or
  policy problem.
- Non-staffing integrity failures still hard-block; fail-open is scoped to
  specialist availability.
- The README "fails loudly" promise is honored by the truthful header and
  persisted receipt, not by blocking the host.

## Alternatives

- **Keep the hard block (ADR-0122 as written).** Rejected because it bricks the
  host on ordinary staffing hiccups and the misleading message sent operators
  chasing a healthy provider.
- **Fail open, but stay uninvolved when no provider is configured.** Rejected as
  a needless special case: the honest header covers both states, and a missing
  provider is one of many valid zero-specialist causes.
- **Add a config toggle (`on_failure=open|block`).** Rejected as premature; the
  hard-block mode had no demonstrated user value and fail-open is the safer
  default. A toggle can be added later if a strict mode is needed.
