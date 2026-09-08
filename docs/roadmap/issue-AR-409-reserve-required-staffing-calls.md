---
title: "AR-409: Reserve required staffing calls before optional work"
status: in_progress
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, inference, budgets, reliability, performance]
related:
  - docs/roadmap/acceptance/issue-AR-409.md
  - docs/roadmap/handoffs/issue-AR-409.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/decisions/0235-reserve-required-staffing-calls-before-optional-work.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-409
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/735
depends_on: [AR-408]
blocks: [AR-404]
---

# AR-409: Reserve required staffing calls before optional work

## Problem

The shared staffing call limit is enforced, but optional subject work and
earlier repairs can consume capacity needed by later mandatory stages.
Claude failure receipt `3615c4fb-1c2f-4a9c-b76f-bd8638f59385` contains two
subject attempts, one planner and two recruiter attempts under strict's
five-call limit. No call remains for the required critic. AR-408 owns the
misleading critic-veto diagnosis; this issue owns allocation within the same
unchanged limit.

ADR-0132 funds the original planner/recruiter repairs and reserves strict's
fifth call for its critic. ADR-0197 later adds a gated subject call. That
subject inherited two semantic attempts per provider and a fallback chain;
neither decision specified how those attempts share the earlier envelope.

## Current state

The reviewed implementation is checkpointed on
`codex/ar409-reserve-required-staffing`, integrated through accepted AR-408
checkpoint `ae916dd1` and main `f408b6f2`. It is not yet on main or activated in
the owner's harnesses. Package phase: demo_ready; source review, bounded receipt
recheck, combined-candidate integration and all five isolated source criteria
are complete. Installed live delivery remains pending. Tracker #735 and the filing records are published separately
from the reviewed implementation so tracker parity does not depend on its merge.

Fixed-response tests now run subject1 + planner1 + recruiter2 + critic1 within
five calls. They also demonstrate that subject1 + planner2 + recruiter2 +
critic1 needs six: with five, the runtime refuses a recruiter repair after
four calls instead of spending the last call on an uncriticizable team.

The full 188-mutation evaluation passed before a final receipt-only refinement.
After that refinement, the five-mutation subset containing the four new
reservation anchors and existing fast-budget control passed. The acceptance
record preserves exact commands, unsuccessful intermediate runs and source scope.
Claude satisfied criteria 1–4, then its executable namespace again became
group-writable. A separately authorized supported Codex-verifier invocation
satisfied only the missing fifth criterion against the same `f670e6b5` candidate;
no completed check was rerun. All five are satisfied; status remains in_progress
until the required installed combined-candidate live checkpoint is recorded.

Source publication: [PR #739](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/739).
This PR references #735 without closing it. All five source criteria are
satisfied; installed owner-harness delivery remains a separate required gate.

## Approach

Keep one owner-configured workforce ledger. With `R = maximum - used` and
`C = 1` in strict mode, otherwise zero, admit an actual call only when
`R > reserve`:

| Stage | Reserved downstream calls | Additional stage bound |
|---|---:|---|
| Subject | `2 + C` | One actual call across the provider chain |
| Planner | `1 + C` | Existing per-provider semantic attempts |
| Recruiter | `C` | Existing per-provider semantic attempts |
| Strict critic | `0` | Existing per-provider semantic attempts |

Refund only transport refusals that report no actual request. Preserve the
zero-signal trigger, prior subject reuse, deterministic validators and the
required critic. Cache hits are read before their own stage's admission check;
the critic remains fresh. Do not preempt hybrid recall just because a future
recruiter call might be unavailable: its output binds the recruiter cache.

Append the closed `workforce_call_budget_exhausted` cause to failed staffing
when it would otherwise be lost before durable receipt projection. Preserve
existing status, verifier causes and units; never manufacture a critic veto.

This retains quality checks, not a guarantee of equal model outcomes. Mandatory
floors are conservative before future cache hits or inferred gaps are known,
so some repair paths abstain sooner. Defaults, explicit owner caps, provider
profiles, deadlines, separate recall/hiring budgets, hiring reviews and all
selection authority remain unchanged. There is no paired live quality or
end-to-end latency-equivalence claim.

## Dependencies

AR-408's truthful failure/timeout projection is integrated. Its exhausted-critic
test now replays the actual exhausted critic boundary while preserving its
committed pre-fix live provenance; its projection fixture funds a real attempt.
ADR-0235 reconciles ADR-0132 and ADR-0197 without retiring their unchanged rules.
AR-401's shared deadline and AR-383's subject/context projection remain intact.

Before completion, commit the implementation and ledger, freeze acceptance to that candidate,
obtain isolated verdicts and run the bounded installed combined-candidate live
checkpoint. Existing AR-404 live evidence is historical motivation, not proof
that this uninstalled candidate is live.

## Acceptance

- [ ] A single unchanged owner-configured workforce call budget admits calls only above the subject `2+C`, planner `1+C`, recruiter `C` and critic-zero downstream floors; explicit limits/defaults remain intact, pre-request refusals refund capacity, and real attempts, repairs and fallbacks never exceed the limit.
- [ ] Subject inference retains the existing zero-signal trigger and prior-subject reuse, spends at most one actual call across its provider chain, permits refunded pre-request fallback, and carries valid hints to later stages without inventing hints when inference fails.
- [ ] Planning/recruitment validation and strict criticism remain mandatory: the fixed-response former five-call failure now reaches a real approving critic within five calls; no-subject planner and recruiter repairs still fit their existing defaults; genuine critic veto/repair behavior remains; mathematically insufficient paths refuse work without deterministic staffing or skipped validation.
- [ ] Exact validated stage-cache hits are usable before their own call-admission checks and never cache away the strict critic; early zero-call and recruiter-reservation failures persist the closed budget cause through real Store receipts, preserving existing status/verifier causes without duplicates or a false critic veto.
- [ ] Focused staffing, subject, deadline, transport, cache and hiring regressions pass; the four curated reservation mutations and existing default-repair control are killed, with the routing evaluation and all evidence explicitly scoped to their tested candidate rather than claimed as paired live model-quality equivalence.
