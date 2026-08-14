---
title: "AR-124: Integrate lifecycle assurance, native delegation, and provider evidence"
status: done
category: roadmap
created: 2026-07-21
updated: 2026-08-12
tags: [delegation, assurance, providers, receipts]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-124
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/137
depends_on: [AR-121]
blocks: [AR-125]
---

# AR-124: Integrate lifecycle assurance, native delegation, and provider evidence

## Problem

Assurance must be triggered by actual artifacts and native child agents must
consume parent-approved staffing without repeating inference or losing exact
provider/model evidence.

## Current state

Native hooks, child activation receipts, shared routing, and model receipts
exist, but planning and assurance are not yet lifecycle-driven end to end.

## Approach

Bind reviewers and verifiers to artifact transitions; project exact-version
recipes through each host bridge; retain host delegation ownership; reconcile
provider, router, requested, and actual model; and bound cache, concurrency, and
new-child inference.

## Dependencies

AR-121 supplies validated staffing plans and lifecycle timing.

## Acceptance

- [x] Assurance agents activate only after their required artifact exists.
- [x] Conflicting methods never share a forbidden context.
- [x] Planned native children consume one-use parent activations without rerouting.
- [x] Provider/router/actual-model evidence is accurate across every supported host.

This is evidence for the historical one-use-activation mechanism. That
transport was later retired; the current vision requires host-owned spawn and
host-authored delivery evidence under ADR-0156.
