---
title: "AR-355: Deliver the owner's working agreements as a second resident manager and make the steward roster-aware"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [resident-managers, steward, prompt-surface, governance]
related:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-355
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/422
depends_on: []
blocks: []
---

# AR-355: Deliver the owner's working agreements as a second resident manager and make the steward roster-aware

## Problem

The owner wants two things on every turn, on every host: (a) five
engineering working agreements, and (b) the steward to be
agency-aware. Today the only every-turn, cross-host injection surface
Agency owns is the resident-manager channel, and it carries exactly one
manager (`agency-steward`), whose kernel is deliberately a short
governance contract (turn framing, evidence boundary,
anti-self-staffing). Folding conduct norms into the steward would
dilute a contract where every line binds, and kernel edits are
versioned events (the kernel hash is pinned in bindings and header
contracts), so the wording could not be tuned without a release.

## Owner authorization

Design agreed with the owner 2026-09-01 in-session: a second resident
manager carrying the working agreements, config-sourced so the owner
edits wording without a code release; plus one descriptive
roster-awareness line in the steward (kernel v5). Awareness only — the
steward must never imply or instruct delegation: staffing identity
comes from recorded inference, and a delegation-nudging steward would
push hosts toward self-staffing (the failure class the critic and
AR-265 exist to prevent).

## Proposed working-agreements manager text (owner-editable)

> [Working agreements — owner]
> 1. Ask, don't assume. When something is unclear, ask before writing a
>    line. Never make silent assumptions about intent, architecture, or
>    requirements. Running unattended, pick the most reasonable
>    interpretation, proceed, and record the assumption rather than
>    blocking.
> 2. Implement the simplest solution for simple problems and better
>    solutions for harder problems. Do not over-engineer or add
>    flexibility nothing needs yet.
> 3. Do not touch unrelated code — but surface bad code and design
>    smells you discover to the owner as separate recorded issues.
> 4. Flag uncertainty explicitly (see 1). Where it helps, run a small,
>    localised, low-risk experiment and bring the hypothesis and
>    results for discussion. Confidence without certainty causes more
>    damage than admitting a gap.
> 5. Better ideas are always welcome — especially durable improvements
>    over tactical changes. Do not hesitate to suggest one.

## Proposed steward addition (kernel v4 → v5, one line)

> A governed workforce of specialists exists. When this turn's capsule
> names specialists, treat them as present expertise; when it names
> none, the turn is honestly unstaffed.

## Approach

1. Discover how resident managers are defined, hashed, and delivered
   (`RESIDENT_MANAGER_SLUG_SET`, kernel rendering, the `managers=` list
   in the binding line) and what pins the kernel hash (bindings, header
   contract, batteries).
2. Add a `working-agreements` manager whose body loads from
   owner-editable config (default text above shipped as the fallback),
   with its own content hash in the binding line for auditability.
3. Bump the steward kernel to v5 with the single roster-awareness line;
   re-wire and battery per the version-change discipline (AR-337).
4. Budget check: measure the added per-turn tokens on the smallest
   context host (hermes) before shipping.

## Dependencies

- Owner review of the two text blocks above before implementation.

## Acceptance

- [ ] Every staffed and unstaffed turn on all four hosts carries the
      working-agreements manager alongside the steward, and its text is
      changeable through owner config without a code release.
- [ ] The steward carries the roster-awareness line and still never
      implies delegation; the anti-self-staffing language is unchanged.
- [ ] Kernel v5 lands through the version-change discipline (re-wire +
      battery), with the binding line reporting both managers and
      their hashes.
- [ ] Per-turn token cost of the addition is measured and recorded.
