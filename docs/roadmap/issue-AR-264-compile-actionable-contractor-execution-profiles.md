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
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
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

- Employment-contract and prompt-template v2 are implemented. New live hiring
  requires the closed profile while parser/compiler v1 remains replay-only.
- All 15 packaged contractors carry reviewed role-specific inspect, principle,
  failure, verification, and stop guidance. The exact assigned work unit still
  arrives separately from the native host.
- Compiler v2 emits a readable worker capsule and omits recruiter-only nearest
  worker and evaluation material. The TypeScript capsule is 2,710 bytes at
  `contractor-2-6b0d5cae3b65a44d`.
- Pull request [#314](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/314)
  merged as exact main `da851c65`; no hosted run was dispatched. Installing
  that revision into Claude exposed that all 15 real package-v1 workers were
  preserved instead of advanced, so live completion stopped before Codex,
  ZCode, dashboard, or provider draws.
- The exact-main defect was a synthetic predecessor: the migration test minted
  the post-August-6 canonical version, while the real Store retained the older
  `contractor-1-sha256:<9 hex>` package identity. The backend contract also had
  pre-v2 capability and evidence fields that could not be reconstructed by
  merely deleting its execution profile.
- The repair pins all 15 historical v1 prompt hashes, reconstructs the two
  version identities that actually shipped, and revalidates prompt bytes,
  immutable revision metadata, and the current recruitment contract inside the
  Store transaction. Unknown Agency amendments and operator projections remain
  preserved.
- A transactionally backed-up disposable copy of the owner Store advanced
  15/15 workers, advanced none on its second pass, retained two-version lineage
  for every worker, and preserved TypeScript's two accepted outcomes and 2/3
  promotion readiness. The real Store's size, mtime, and SHA-256 were unchanged.
- Specialist prompt reads now decode exact active revision metadata, and the
  dashboard overlays its real `evidence_requirements` into owner detail.
- The original named local fast spine reports 806 passed and 20 skipped. The
  repair's widened contractor, Store, installer, hiring, and selection suite
  reports 332 passed and one skipped; focused Ruff and diff checks pass. The
  full post-repair local spine remains the next checkpoint.
- Tracker [#313](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313)
  is linked under explicit owner authorization. Non-draft pull request
  [#314](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/314)
  publishes the clean candidate to `main` and is explicitly authorized to
  merge; installation and live smoke testing remain separately authorized.

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

- [x] Employment-contract v2 requires a closed, bounded execution profile and
      rejects control-channel prose, hidden controls, unknown fields, and
      generic empty guidance.
- [x] The current hiring inference asks for reusable role-specific execution
      data without adding another provider call or allowing raw prompt output.
- [x] Compiler v2 renders readable inspect, working-method, failure, evidence,
      and stop sections while excluding recruiter-only comparison/eval fields.
- [x] Historical employment-contract v1 evidence still parses and compiles to
      the exact prior prompt bytes and hashes, including both package version
      identities that shipped.
- [x] Packaged contractors carry reviewed execution profiles, and reinstalling
      over either exact v1 package identity advances them through immutable,
      auditable, idempotent lineage while preserving amended contract metadata.
- [x] Workforce detail and the dashboard show the active revision's real
      evidence requirements; `none recorded` appears only when none exist.
- [x] Focused contract, hiring, Store, dashboard API, and dashboard UI tests
      pass with Ruff and documentation validation.
- [x] Tracker issue #313 is created and linked after explicit authorization.
- [ ] The repaired candidate is merged to main, installed into Claude, Codex,
      ZCode, and the dashboard, and smoke-tested under the current live-operation
      boundary. OpenClaw and Hermes remain deferred to the Linux handoff.
