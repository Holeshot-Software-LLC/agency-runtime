---
title: "Project qualified critic veto causes with an omission marker"
status: accepted
category: decisions
created: 2026-09-08
updated: 2026-09-08
tags: [critic, diagnostics, headers]
related:
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/worklog/README.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
supersedes: []
superseded_by: null
id: ADR-0240
type: decision
deciders: [owner]
---

# ADR-0240: Project qualified critic veto causes with an omission marker

## Context

The strict critic accepts bounded128character hyphenated reason codes, while
its receipt projection permits56characters including the `critic_` prefix.
A real named-neighbor veto exceeded that bound and silently lost its cause.
Four maximally bounded projected codes must still fit the512character disclosure.

## Decision

Retain exact short projections. When a valid critic reason is too long, preserve
a recognized standard veto ground only when it is the code's full prefix ending
at a hyphen boundary. Add `critic_reason_detail_omitted` rather than silently
discarding the qualifier. Unknown oversized codes receive only that marker.
The existing count, charset, length, receipt and disclosure validators remain.
The projection never changes a critic decision, selects a worker or rewrites
an existing terminal receipt.

## Consequences

A qualified wrong-neighbor veto retains its standard cause. The header explicitly
admits omitted detail; the captured packet remains the evidence for the full
qualifier. Long unknown codes remain bounded and visibly incomplete. Existing
short codes and accepted responses are unchanged.

## Alternatives

Widening every downstream bound risks the fixed disclosure budget. Truncating
identities can manufacture misleading codes. Silently dropping the entire cause
makes valid diagnostic evidence disappear. None is adopted.
