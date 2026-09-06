---
title: "Bound delivery to live demo checkpoints"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [governance, delivery, testing, demo, cost]
related:
  - docs/roadmap/issue-AR-129-isolate-subprocess-environments.md
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/decisions/0223-retire-superseded-zcode-stop-checklist.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-406-restore-dashboard-function-coverage.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
  - AGENTS.md
  - CONTRIBUTING.md
  - docs/RELEASE_CHECKLIST.md
  - docs/NORTH_STAR_ACCEPTANCE.md
supersedes:
  - docs/decisions/0101-run-exhaustive-python-verification-on-demand.md
superseded_by: null
id: ADR-0105
type: decision
deciders: [maintainers]
---

# ADR-0105: Bound delivery to live demo checkpoints

## Context

An umbrella production-readiness task repeatedly expanded when each audit found
more cleanup, every cleanup invited another audit, and release language required
an expensive exhaustive workflow at the final commit before any `GO`. The loop
made it difficult to see the installed product working and spent time and CI
budget without a hard observable checkpoint.

The exhaustive suite remains useful when a maintainer wants broad diagnostic or
coverage evidence, but it is not the only credible evidence. Focused
warning-strict tests, the named fast production spine, artifact verification,
fresh installation smoke, and a live host/UI trace directly test a bounded
delivery claim.

## Decision

Every delivery package begins with one observable outcome and follows:
`scoped → implementing → focused_review → fast_verification → demo_ready →
live_demo → done`. `blocked` and `waiting_for_operator` are explicit exits.

Only findings that invalidate the stated outcome remain in the package.
Unrelated findings are recorded for later work. Two independent review passes
are the default maximum; additional review requires unresolved Critical/High
evidence or an explicit owner request. A package reaches its live-demo checkpoint
before broad documentation cleanup, optimization, or secondary certification.

The complete warning-strict corpus, four-shard coverage, and compatibility
matrix remain available only through an explicitly requested manual workflow.
They are optional diagnostics, not mandatory issue-completion, demo, production,
or release gates. Their absence is reported when relevant but does not itself
force `NO-GO`. A verdict instead names its exact scope and cites the applicable
fast checks, artifact evidence, live behavior, security findings, and known
limitations.

A step that needs user presence, trust approval, credentials, signing authority,
or an external decision enters `waiting_for_operator`; it is reported once and
is not retried in an unattended loop.

## Consequences

- Users see a working exact artifact earlier and can evaluate real behavior.
- Review remains serious, but secondary findings cannot indefinitely expand one
  package.
- Routine and hosted test spend remains bounded; maintainers can still request
  exhaustive evidence when its value justifies the cost.
- `GO` statements become scope-specific rather than dependent on one universal
  certification job.
- Human-owned boundaries remain honest and visible without being mislabeled as
  failed autonomous execution.

## Alternatives

- **Keep exact-final-commit exhaustive CI mandatory.** Rejected by the owner
  because its time and hosted-minute cost prevent timely live validation.
- **Remove exhaustive workflows.** Rejected because they remain valuable when
  explicitly requested for diagnostics or coverage analysis.
- **Continue until every review finding is fixed.** Rejected because it creates
  an unbounded loop and delays the observable product checkpoint.
- **Retry human-owned steps autonomously.** Rejected because repetition cannot
  supply presence or authority and obscures the actual waiting state.
