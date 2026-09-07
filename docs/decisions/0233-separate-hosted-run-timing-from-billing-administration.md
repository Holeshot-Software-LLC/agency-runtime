---
title: "Separate hosted-run timing from billing administration"
status: accepted
category: decisions
created: 2026-09-07
updated: 2026-09-07
tags: [ci, acceptance, evidence, billing, governance]
related:
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/roadmap/acceptance/issue-AR-174.md
  - docs/roadmap/acceptance/evidence/AR-174-docs-only-ci-20260907.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/decisions/0100-short-circuit-trusted-docs-only-pull-requests.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0233
type: decision
deciders: [maintainers]
---

# ADR-0233: Separate hosted-run timing from billing administration

## Context

AR-174's implemented shortcut is a fail-closed docs-only CI lane, not account
billing administration. The owner requested oldest-first evidence-led backlog
reconciliation, including deciding whether old agent-written requirements
remain relevant. The July 27 criterion asked for one eligible hosted PR's raw
runner minutes after a then-reported billing/spending block was repaired.

Fresh September 7 readback in 452639dd identifies August 31 PR #380/run
33426445699: exact regular Markdown delta, five allocated successful runners
and 366 seconds of raw job time. The first isolated review preserved at
5d20ec28 correctly distinguishes those observations from proof of a billing
account repair. A successful run neither identifies who changed billing nor
establishes current account health. No such authority or private billing proof
was supplied, and the local builder must not invent it.

## Decision

Reconcile only AR-174 criterion 7 to require one exact eligible hosted
pull-request run with raw runner minutes derived from allocated jobs' recorded
start/completion timestamps. Bind the run ID/attempt, PR base/head, complete
regular docs-only delta and successful five-runner topology. Preserve raw
timestamps and the exclusion of unallocated skipped placeholders.

An honestly dated historical run may satisfy this single measurement
obligation; it is not a current-candidate CI result. Do not infer billing
repair, billing health, rounded billed minutes, platform multipliers, matched
before/after savings or current hosted enforcement from it. Keep those claims
separate and demand their own evidence if made.

Keep the original criterion and first verdict in Git. Criteria 1–6 remain
unchanged; criterion 8 already follows ADR-0105's bounded delivery policy.
Neither the scope classifier, artifact requirements, analyzer paths nor hosted
settings change. This supplements ADR-0100 without superseding its runtime
authority. AR-156/159's remaining accepted obligations stay open.

## Consequences

- The measured CI behavior and billing-account administration are no longer
  conflated. An irrelevant inferred account-state claim does not make a
  successfully measured product behavior permanently unfinished.
- One historical observation does not promise present service availability or
  general speed/cost savings. No native Windows work is performed by readback.
- A new frozen candidate receives isolated verdicts under the explicit revised
  requirement; the first results are retained, not retroactively relabeled.

## Alternatives

- **Claim successful allocation proves billing was repaired.** Rejected:
  observed job execution does not establish account-state causality.
- **Require credentials or billing changes for this code issue.** Rejected:
  that expands the product outcome into separately authorized administration.
- **Accept structural runner counts without a run.** Rejected: actual timestamp-
  bound hosted measurement remains required and is available.
- **Silently drop the old wording or reuse verdicts.** Rejected: preserve the
  requirement, reconciliation and first review, then verify the final candidate.

## Acceptance evidence

All eight final AR-174 criteria satisfy at 5a003a05, with first verdicts retained
at 5d20ec28. This records measured historical execution, not account-state repair.
