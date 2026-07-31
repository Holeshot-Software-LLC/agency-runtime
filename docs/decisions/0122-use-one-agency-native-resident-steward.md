---
title: "Use one Agency-native resident steward"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-07-30
tags: [orchestration, managers, inference, roster, activation]
related:
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - README.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
superseded_by: null
id: ADR-0122
type: decision
deciders: [maintainers]
---

# ADR-0122: Use one Agency-native resident steward

## Context

ADR-0065 correctly separated a compact resident-management kernel from
ordinary specialist execution, but assigned that universal responsibility to
two imported upstream roles. Their actual audited scopes are narrower than
every Agency-enabled turn. The arrangement made the upstream roles protected,
unconfigurable, and visibly loaded even when neither role matched the request.

Agency still needs one small parent contract that preserves the user outcome,
acceptance boundary, and evidence discipline before inference has selected any
specialist. That role is product infrastructure, not a workforce candidate.

## Decision

Use one Agency-native, parent-only `agency-steward` as the always-resident
default. Its compact, versioned kernel owns:

- the requested outcome, scope, priorities, constraints, and acceptance gates;
- the boundary requiring a recorded inference decision before any specialist
  identity is accepted;
- current-turn evidence, lifecycle, and fail-loud completion discipline; and
- the handoff from an accepted staffing decision to the native host.

The steward does not select, rank, hire, schedule, execute, review, or claim
specialist activity and does not answer the domain request. Inference owns staffing;
deterministic code may retrieve
candidates and reject unsafe proposals; the native host owns worker lifecycle.
The steward is not an ordinary roster entry and cannot be loaded or delegated
as a specialist.

`agents-orchestrator` and `chief-of-staff` remain installed audited roster
members. They are ordinary, disableable specialists selected only by valid
inference for their positive and negative activation contracts. Orchestrator
fits multi-specialist decomposition and delegation design. Chief of Staff fits
sustained program or executive coordination. Neither is a universal default.

The recruiter receives the complete bounded `scope_qualifiers` and `not_for`
metadata. These fields inform inference and reject incompatible nominations;
they do not become deterministic selection rules. There is no deterministic
no-match worker fallback.

Every substantive question or action requires a selected specialist. When the
roster has no defensible match, inference declares the missing specialty and the
hiring stage may create a narrowly scoped contractor for that exact work unit.
Task-scoped expertise is sufficient; broad generalism or a pre-created persona
is not required. The contractor must still have bounded authority, exclusions,
and evidence requirements. If selection, hiring, or verification cannot produce
that receipt, Agency fails before accepting a domain answer.

The conceptual workforce is open-ended. Recruiter inference first defines the
ideal specialist an exacting owner would want for the work unit and only then
tests installed candidates against that ideal. The installed roster is a cache
of reusable audited specialists, not a finite taxonomy that forces a nearest
generalist. Gap-hiring inference materializes a missing ideal role.

## Consequences

- Every enabled turn retains a small stable management and evidence boundary.
- The visible default no longer implies that two unrelated imported agents
  matched every request.
- Owners can opt either imported coordination specialist out like any other
  roster member.
- Positive and negative activation criteria affect staffing through inference
  plus reject-only verification, not a hidden keyword selector.
- A missing or invalid inference decision remains a loud zero-specialist
  outcome even though the steward is resident.
- Resident-only completion cannot turn the parent model into a generalist;
  substantive work is specialist-staffed or terminally unavailable.
- Existing resident bindings become stale when the kernel version/hash changes
  and are re-injected through the existing lifecycle.

## Alternatives

- **Keep the imported pair resident.** Rejected because their own audited
  activation scopes are not universal.
- **Make every turn have no resident default.** Rejected because the user
  contract and evidence boundary would become implicit and host-dependent.
- **Put the steward in the selectable roster.** Rejected because infrastructure
  authority must not masquerade as workforce execution.
- **Convert activation criteria into deterministic rules.** Rejected because
  that would recreate the selection system ADR-0118 removed.
