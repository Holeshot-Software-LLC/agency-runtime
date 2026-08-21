---
title: "AR-264: Compile actionable contractor execution profiles"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [contractors, hiring, prompts, workforce, dashboard, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-264
priority: p0
tracker_url: null
depends_on: [AR-122, AR-123]
blocks: [AR-119]
---

# AR-264: Compile actionable contractor execution profiles

## Problem

Agency's governed contractor prompt establishes identity, scope, authority,
capabilities, exclusions, and evidence boundaries, but it gives the executing
child little role-specific working method. The fixed template serializes the
entire employment contract as dense JSON, including recruiter-only comparison
and evaluation metadata. It therefore constrains and identifies the worker
without guiding execution as clearly as the audited resident specialist cards.

The dashboard compounds that ambiguity by rendering `Evidence required: none
recorded` for packaged contractors even though their immutable revision
metadata and compiled prompt contain explicit evidence requirements.

## Current state

- Hiring inference is correctly forbidden from authoring executable prompt
  prose. It returns a closed structured employment contract that an independent
  critic and safety reviewer inspect.
- Contractor prompt template v1 embeds the complete contract JSON beneath six
  generic operating rules. The exact assigned work unit is delivered separately
  by the native host.
- The known TypeScript contractor names type-system design, async Node.js,
  runtime validation, and build/test tooling, but supplies no inspect-first
  method, failure-mode checklist, or concrete execution sequence.
- Packaged contractors already persist `evidence_requirements` in immutable
  revision metadata. Workforce contract v2 intentionally omits that
  execution-only field, while the dashboard incorrectly reads it from the
  workforce projection.
- Existing installations retain immutable contractor prompt v1 revisions. A
  package change cannot rewrite those rows and the current installer does not
  advance a known contractor whose packaged prompt changed.

## Approach

Add a closed, bounded employment-contract v2 `execution_profile` containing
role-specific inspect-first checks, working principles, failure modes,
verification steps, and stop conditions. Inference returns these fields as
untrusted structured data, never as a raw prompt. The fixed compiler owns the
instruction syntax and renders a readable execution capsule containing only
worker-relevant material; closest-worker comparisons and selection evaluations
remain recruiter evidence and do not enter child context.

Retain exact v1 parsing and byte-identical v1 compilation for historical or
pending hiring evidence. New inference candidates and packaged contractors use
v2. Advance an already-installed packaged v1 contractor through an auditable,
idempotent package-owned amendment that preserves its worker identity, prior
version, lineage, outcomes, and rollback evidence.

Project dashboard evidence requirements from the exact active revision
metadata already retrieved with the specialist prompt. Do not widen the compact
whole-workforce recruiter contract merely to repair an owner detail view.

## Dependencies

- AR-122 owns governed structured hiring, fixed compilation, and lifecycle.
- AR-123 owns truthful CLI and dashboard workforce detail.
- ADR-0081 forbids unrestricted inference-authored executable prompts.
- ADR-0162 defines the data/compiler boundary and immutable upgrade path.

## Acceptance

- [ ] Employment-contract v2 requires a closed, bounded execution profile and
      rejects control-channel prose, hidden controls, unknown fields, and
      generic empty guidance.
- [ ] The current hiring inference asks for reusable role-specific execution
      data without adding another provider call or allowing raw prompt output.
- [ ] Compiler v2 renders readable inspect, working-method, failure, evidence,
      and stop sections while excluding recruiter-only comparison/eval fields.
- [ ] Historical employment-contract v1 evidence still parses and compiles to
      the exact prior prompt bytes, hash, and version identity.
- [ ] Packaged contractors carry reviewed execution profiles, and reinstalling
      over v1 advances them through immutable, auditable, idempotent lineage.
- [ ] Workforce detail and the dashboard show the active revision's real
      evidence requirements; `none recorded` appears only when none exist.
- [ ] Focused contract, hiring, Store, dashboard API, and dashboard UI tests
      pass with Ruff and documentation validation.
- [ ] A tracker issue is created and linked after explicit authorization.
- [ ] The reviewed candidate is merged, installed, and smoke-tested only after
      separate publication and live-operation authorization.
