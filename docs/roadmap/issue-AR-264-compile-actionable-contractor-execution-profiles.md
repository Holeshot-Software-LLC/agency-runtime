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
  merged as exact main `da851c65`; installing it exposed that all 15 real
  package-v1 workers were preserved instead of advanced.
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
  promotion readiness. Pull request
  [#315](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/315)
  merged that repair as exact main `f76050d7`; both PRs used `[skip ci]` and
  no hosted workflow ran.
- Before exact-main installation, the owner Store was copied to
  `pre-ar264-f76050d7-20260821T171621.410934Z.db` with SHA-256
  `9b9936456e90313b76920a4dfd3890c7c44b0243d4a2781592182325aa2bcdaa`.
  The real installation then upgraded all 15 known packaged contractors to
  revision 1 / contract v2 / two-version lineage. TypeScript retained its two
  accepted outcomes and 2/3 promotion readiness.
- Specialist prompt reads now decode exact active revision metadata, and the
  dashboard overlays its real `evidence_requirements` into owner detail.
- The repaired candidate passes all 14 governing local gates in 16.5 minutes:
  806 passed and 20 skipped in the production spine, 695 passed in AR-119
  matrix evidence, 161 passed in workflow contracts, and all 134 dashboard UI
  tests meet the configured coverage thresholds. The deterministic routing
  evaluation passes every correctness, safety, performance, and scale gate.
  Linux behavior, integration coverage shards, and the hosted-only mutation
  phase remain outside this local package.
- Exact main `f76050d7` is freshly installed for Claude, Codex, ZCode, and the
  dashboard. Their current bundle digests are `2eaa89cc75f8...`,
  `75f6519c74ba...`, and `2f1bb95ba204...`; all three native projections are
  current and report no configuration drift.
- After the reboot, the existing dashboard task was registered and current but
  stopped. Starting that owned task restored authenticated health. Dashboard
  and CLI then returned the same 31 contractor rows at digest
  `401e883532e9...`; after one bounded background host refresh, all five host
  rows matched at digest `003caceee19d...`, and master generation 56 matched.
- Skill capture is provider-free proven on this exact tree: three focused hook
  cases pass for Claude, Codex, and ZCode, each injecting its loaded skill into
  the first-pass header. The owner Store contains 19 historical skill-load
  rows. A fresh post-install Codex Desktop skill header remains a new-task
  lifecycle check, not evidence available from this already-running task.
- The single exact-main Codex activation draw stopped at parent preflight
  `workforce_inference_failed` after valid planner and recruiter responses; it
  produced no routing decision, child, delegation, delivery, or final header.
  The single ZCode draw exited 0 and started generic host child
  `agent_469477bd-...`, but Agency trace `37bdf697-...` failed its ordinary
  planner through the expired `claude-subscription` before staffing. Its host
  artifacts contain zero Agency v6 delivery markers. Neither draw was retried.
- Claude CLI remains logged out. That operator boundary blocks a fresh Claude
  staffing/hiring draw and also blocks ZCode's ordinary parent planner before
  the separately pinned GLM child judge can be reached. Provider routing was
  not changed, no accepted outcome or hire was claimed, and no AR-119 matrix
  cell moved.
- Tracker [#313](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313)
  remains open until the fresh-task and authenticated live boundaries above
  are completed.

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
- [x] The repaired candidate is merged to main, migrates the owner Store from
      both shipped package-v1 identities, is freshly installed into Claude,
      Codex, ZCode, and the dashboard, and has exact dashboard/CLI parity.
- [ ] Fresh authenticated Claude, Codex, and ZCode tasks produce Store-backed
      parent headers and complete the bounded staffing, skill, hiring, and reuse
      smoke. OpenClaw and Hermes remain deferred to the Linux handoff.
