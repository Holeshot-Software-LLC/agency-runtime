---
title: "AR-408: Preserve truthful staffing failure and effective deadline receipts"
status: done
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, inference, diagnostics, deadlines, reliability]
related:
  - docs/roadmap/handoffs/issue-AR-408.md
  - docs/roadmap/acceptance/issue-AR-408.md
  - docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md
  - docs/roadmap/issue-AR-409-reserve-required-staffing-calls.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/routing_projection.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-408
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/732
depends_on: []
blocks: [AR-409]
---

# AR-408: Preserve truthful staffing failure and effective deadline receipts

## Problem

A turn can report that its critic rejected staffing when the critic never ran.
Effective provider timeout evidence also disappears between an inference
attempt and the durable failure receipt. Both defects obscure the cause of
slow or unsuccessful staffing, even though the runtime knows it.

## Current state

Live Claude trace `3615c4fb-1c2f-4a9c-b76f-bd8638f59385` spent five calls:
two rejected subject responses, accepted planner, rejected recruiter and
accepted recruiter repair. The configured strict call limit is five. There is
no critic attempt, but the durable reason is `staffing_critic_rejected`.
The same source routes all critic invocation failures through a veto helper.

Separately `WorkforceInferenceAttempt.timeout_ms` is populated, and the
downstream failure allowlist supports it, but workforce routing projection
omits the field. The September 7 Hermes timeout therefore retains120206ms
elapsed without its120000ms allowance. The actual Hermes preflight took
270035ms, of which268046ms were provider attempts; its generated595s hook
has a585s shared inference budget. This is not evidence of a75s deadline
violation or large local serialization overhead.

The reviewed implementation reproduces both defects without new provider
requests and corrects classification and allowance projection. Focused325
pass/one skip/one deselection; independent32 pass/no findings; fresh named
spine1085/three existing skips and UI224 pass. See the
[bounded evidence receipt](acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md).
All three isolated criteria satisfy at frozen candidate d9dde3cd. The exact
portable artifact also passes installed CLI/MCP/dashboard and all five
generated-host smoke contracts (8 pass, zero failures/skips in5.03s). Normal
PR/merge and tracker closure are next; no native model success is inferred.

## Approach

Keep a real valid negative critic verdict distinct from absence of a verdict
due to budget exhaustion, deadline, unavailable provider or invalid response.
Carry positive effective timeout allowance through the existing bounded
routing/failure projection; an expired pre-call deadline must not claim a
positive allowance. Preserve safe omission of nonpositive allowance values.

No call-budget default, explicit owner limit, semantic selection, mandatory
critic, credential, provider profile or trust policy changes belong here.
A quality-preserving allocation policy is separate follow-up under the existing
workforce repair/performance work, not smuggled into an observability fix.

## Dependencies

ADR-0209 governs truthful cause classification; AR-392/401 already implement
transport and deadline evidence that this projection must preserve.
AR-201 and AR-383 supply the broader budget/subject-stage context.

## Acceptance

- [x] Budget exhaustion before the critic and other failures without a valid critic verdict retain their actual staffing failure instead of claiming a critic veto; genuine veto and approval behavior remain unchanged.
- [x] Effective positive provider timeout survives workforce routing and durable failure persistence, including shared-deadline clipping, while an already-expired pre-call deadline does not claim positive allowance and private response/credential fields remain excluded.
- [x] Focused regressions reproduce the exact five-call live failure sequence, verify the real Store persistence boundary and pass alongside relevant inference/deadline tests without increasing configured budgets or bypassing mandatory review.
