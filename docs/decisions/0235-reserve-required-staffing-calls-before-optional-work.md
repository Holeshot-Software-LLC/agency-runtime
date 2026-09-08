---
title: "Reserve required staffing calls before optional work"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, inference, budgets, reliability]
related:
  - docs/roadmap/acceptance/issue-AR-409.md
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0235
type: decision
deciders: [maintainers]
---

# ADR-0235: Reserve required staffing calls before optional work

## Context

ADR-0132 funds planner initial/repair and recruiter initial/repair, with one
additional strict critic call. Explicit owner limits remain authoritative.
ADR-0197 subsequently places a short subject classification before the planner
only when lexical narrowing has zero signal. Its implementation reused the
general two-attempt-per-provider loop and the same workforce ledger.

The September 7 Claude receipt `3615c4fb-1c2f-4a9c-b76f-bd8638f59385` spent
subject2 + planner1 + recruiter2: strict's five calls were exhausted before
criticism. Subject failure already permits planning with no inferred hints;
it is useful evidence, not staffing authority. AR-408 corrects the separate
false-veto receipt and lost timeout field without changing allocation.

## Decision

Supplement ADR-0132 and ADR-0197 with an explicit admission priority. Do not
retire either decision, rewrite its historical evidence or change the fresh
fast-four/balanced-four/strict-five defaults or any persisted owner value.

Let `R` be remaining calls on the single workforce ledger and `C` be one for
strict, zero otherwise. Before every actual provider attempt, require:

| Stage | Admission condition | Stage-local rule |
|---|---|---|
| Subject | `R > 2 + C` | At most one actual call over the entire chain |
| Planner | `R > 1 + C` | Existing semantic repair and provider ordering |
| Recruiter | `R > C` | Existing semantic repair and provider ordering |
| Strict critic | `R > 0` | Existing valid-verdict and semantic-repair rules |

The subject call cap counts actual requests, not adapter invocations. A
transport refusal with `call_attempted=false` refunds capacity and may advance
to the next configured provider. A response or post-request transport failure
uses its call. No provider chain or semantic repair bypasses a reservation.

Keep the zero-signal trigger and prior-subject reuse unchanged. A failed or
unaffordable subject contributes no invented hints; the planner can continue
within its own admission floor. Do not lower validation, nominate workers
locally, accept an uncriticized strict team or raise a deadline to obtain a
result. A valid negative critic verdict remains a veto, not a repair request.

Validated plan/recruiter cache hits spend no calls and are read before their
own admission checks. Strict criticism is never cached away. Do not assume a
future cache hit while funding an earlier call. In particular, optional hybrid
recall still precedes the recruiter cache identity; this decision does not
authorize discarding that evidence to seek a speculative cache hit.

When an exact budget refusal is known, preserve its closed cause alongside
existing failed staffing reasons through durable projection. Do not change
the generic routing status, erase verifier causes or relabel absence of a
critic verdict as rejection. AR-408 remains responsible for the critic-boundary
and effective-timeout correction.

### Unchanged stage and hiring policy

Planner, recruiter and critic retain at most two semantic attempts per
configured provider; a fallback can add attempts only within the shared
remaining budget. Complete malformed model text, truncation and semantic
rejection retain their existing repair rules. Other transport failures advance
the configured chain without adding a same-provider semantic repair. The
subject's new one-actual-call total cap is the deliberate narrower exception.

Hybrid recall keeps its independent maximum of two embedding calls plus one
reranker; the text reranker still has one semantic attempt. Recall shares the
absolute preflight deadline but cannot consume the workforce call ledger.

Hiring is not reallocated here. It retains its separate configured ledger
(fresh default six), candidate validation, configured hiring critic,
provider-independence policy and isolated security review. The existing hiring replacement reserves one call
for its renewed critic; safety-repair turns remain bounded by the configured
repair budget and re-run security review. No new worker can bypass those
checks. None of these paths gains calls, credentials or execution authority.

## Consequences

Policy filing: `96a048d6`; implementation: `9946461a`, indexed in the worklog.
The separately reviewed implementation integrated AR-408, satisfied all five
source criteria and merged as `4db6be16`. Exact-main owner installation and
bounded native failure evidence are recorded in AR-409's delivery receipt;
successful end-to-end installed staffing remains unproven.

The demonstrated subject2/planner1/recruiter2 exhaustion becomes at most
subject1/planner1/recruiter2/critic1 under the same five-call strict cap, if the
stage-local replies recur. No-subject planner2/recruiter2/critic1 still fits
five. The model, not this admission rule, must supply every accepted result.

Subject1 + planner2 + recruiter2 + critic1 requires six, not five. Reserving
mandatory calls cannot preserve all repair opportunities within an insufficient
cap. The original ADR-0132 two-stage default proof remains valid on its
no-subject path; it never funded an additional classification stage for free.
An owner may deliberately choose a different explicit limit, but this change
does not do so automatically.

Floors are intentionally conservative before later outputs are available. A
future recruiter cache hit could avoid a call, or a repaired proposal could
declare a real gap that enters separate hiring without the staffing critic.
Neither outcome may be presumed to spend that critic's reservation in advance.
Some formerly attempted paths therefore abstain sooner. Preserving safety
checks is not proof of equal staffing quality, hiring success or wall latency.

The implementation has fixed-response, storage and mutation evidence only.
No paired live quality-equivalence result or installed combined-candidate
claim exists in this decision. AR-409 must integrate AR-408 and complete its
publication and bounded live checkpoint before reporting delivery complete.

## Alternatives

- Increase default or persisted budgets silently: rejected; cost/latency caps
  are owner-authoritative, and a larger cap is not the requested bounded fix.
- Reserve only the last critic call but keep two subject attempts: avoids one
  doomed spend but does not rescue the demonstrated five-call response path.
- Remove subject inference: rejected; it discards ADR-0197's chosen input
  improvement for zero-signal requests.
- Skip criticism, relax validation or synthesize a worker/hint: rejected;
  allocation has no selection or approval authority.
- Promise both repairs plus subject within five: rejected; the required
  minimum is six even before critic repair or provider fallback.
- Reorder recall/cache semantics or change hiring reservation policy here:
  deferred; neither is needed for this bounded staffing allocation decision.
