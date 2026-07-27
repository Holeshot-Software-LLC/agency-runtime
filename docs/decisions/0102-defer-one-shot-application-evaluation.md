---
title: "Defer complete-application evaluation without weakening live release evidence"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [evaluation, release, testing, production]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/roadmap/AR-119-live-gates-runbook.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
supersedes: []
superseded_by: null
id: ADR-0102
type: decision
deciders: [maintainers]
---

# ADR-0102: Defer complete-application evaluation without weakening live release evidence

## Context

AR-119 and AR-125 treated six complete one-shot application builds as a release
gate alongside specialist participation, matched evaluation, installed
artifacts, and live host canaries. That broad product-generation corpus is
useful, but it is expensive and does not define whether Agency Runtime itself
selects, activates, and accounts for specialists correctly.

The owner wants the final production push to prioritize fresh runtime evidence
and move complete-application research after launch. Existing evaluator code
remains useful and must not be deleted merely because its schedule changes.

## Decision

Remove complete one-shot application generation from AR-119 and AR-125 closure,
production GO, and release gates. Track it in AR-178 as a P2, non-blocking,
post-production evaluation with fixed matched controls and blind grading.

Keep the production-facing evidence strict: complete per-worker and composition
coverage, configured-inference and held-out matched selection, accepted exact-
version activation receipts, paired Agency-on/off outcome evidence, exact-
candidate Windows/Linux artifact verification, five-host contracts and live
canaries, and zero known Critical or High defects. Invalid, malformed, timed-out,
or missing-receipt evaluation arms remain invalid rather than losses.

If AR-178 later discovers a Critical or High defect, record and govern that
defect independently; deferred scheduling does not waive a defect once known.

## Consequences

- AR-119 and AR-125 can reach production without spending the six-application
  evaluation budget.
- AR-178 preserves the evaluation design and evidence discipline after launch.
- Existing product-evaluation implementation remains available and tested.
- Production readiness still requires fresh live host, artifact, participation,
  selection, and comparative-outcome evidence.

## Alternatives

- **Keep one-shot applications as a release gate.** Rejected by the owner
  because it delays current live validation without defining core runtime
  correctness.
- **Delete the evaluators and corpus.** Rejected because the post-production
  study remains useful.
- **Treat any generated application as proof.** Rejected because unmatched or
  unblinded artifacts cannot establish Agency value.
