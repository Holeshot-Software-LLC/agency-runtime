---
title: "Keep a compact resident manager kernel at the parent boundary"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [orchestration, managers, context, compaction, lifecycle]
related:
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0065
type: decision
deciders: [maintainers]
---

# ADR-0065: Keep a compact resident manager kernel at the parent boundary

## Context

Agency needs stable management authority on every enabled parent turn without
turning a long-running conversation into an accumulation of upstream prompt
bodies. Selecting the managers as ordinary workers also blurs who owns the
outcome, who selects specialists, and who executes a bounded work unit.

## Decision

Represent `chief-of-staff` and `agents-orchestrator` as one small, immutable,
versioned resident-manager contract installed at the host or session boundary.
Bind delivery to a parent turn with a content hash and lifecycle receipt. Restore
that contract once after compaction when its binding is no longer present; never
append both full upstream prompts on every message.

Chief of Staff owns the desired outcome, scope, priorities, constraints, and
completion gates. Agents Orchestrator owns decomposition, compatible specialist
selection, delegation recommendations, and evidence boundaries. Neither manager
is an ordinary specialist, native child, or selectable unit assignee. The native
host alone schedules workers. Specialists execute bounded units, and independent
reviewers remain isolated from implementer directives.

The manager pair is protected and cannot be disabled. Other specialists are
ephemeral and enabled or disabled through the governed activation policy. Header
claims include the managers only when the current parent-turn binding proves
that their compact contract affected the response.

## Consequences

- Parent instructions remain small and stable across long sessions.
- Management authority is explicit without masquerading as worker execution.
- Compaction recovery reloads a hash-bound contract rather than historical
  specialist prompts.
- Children receive their own specialist selection and never inherit the
  resident managers as ordinary directive prompts.
- A missing or ambiguous resident binding cannot be converted into a loaded
  claim.

## Alternatives

- Append both full manager prompts on every turn. Rejected because instruction
  growth eventually weakens adherence and wastes context.
- Select the managers as default specialists. Rejected because management
  authority and bounded worker execution are different roles.
- Remove persistent management contracts. Rejected because delegation and
  completion boundaries would become host-dependent and implicit.
