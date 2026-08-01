---
title: "AR-219: Preserve exact multi-unit Codex product execution evidence"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, codex, delegation, evidence, workspace]
related:
  - README.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_one_shot.py
  - tests/test_codex_activation_canary.py
  - tests/test_product_one_shot.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-219
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/221
depends_on: [AR-218]
blocks: [AR-203, AR-204]
---

# AR-219: Preserve exact multi-unit Codex product execution evidence

## Problem

Exact merged build `f8e607d309f5dba933bc55f17892209e39e6e014`
passes autonomous Codex activation with a real inferred `code-reviewer`, one
completed native delegation, a valid first response header, and zero
corrections. Its one governed `python-cli-service` product trial reaches a much
later boundary: inference accepts eight work units, Codex starts and completes
eight native child workers, and the Store accepts the parent finalization.

The product collaboration projector still returns no accepted projection. Its
content-free diagnostic reports eight spawns, eight waits, sixteen tool
outputs, eight child starts, twenty-four agent messages, zero unexpected items,
and `native_collaboration_topology_invalid`. Because the exact rejected
invariant is discarded, the product grader treats every unit as unevidenced,
rejects the header, and reports no workspace write. The isolated trial
workspace is in fact empty, so the README application-build outcome remains
unproven even though worker lifecycle receipts exist.

## Current state

PR 220 merged the four-call workforce budget and legacy balanced-cap repair as
the exact installed revision above. The named fast gate passed 643 Python tests
with six skips, 110 dashboard UI tests, every routing gate, and 73/73 killed
decision mutations with zero survivors or invalid cases. The default suite is
installed for Codex and ZCode, and the dashboard service is installed, active,
current, and reachable.

Autonomous activation passed on its first attempt in session
`019fbc48-be72-7442-9fa0-be195fcffffb`, trace
`019fbc48-cb46-7c73-a835-23477439beb6`, run
`b1cfda5a-19c8-4615-8bd5-5c628053229a`, and route
`9ad116c3-311d-4a6b-ac40-698cce7fd7e1`. Trust mode was
`autonomous_bypass`; the persistent profile did not change.

Trial `ar218-f8e607d-readme-01` is consumed and terminal `NO-GO` after 427.3
seconds. Session `019fbc4c-aeae-70c1-b256-f166e92452c5`, trace
`019fbc4c-af63-76c0-9a40-55a559c4fee4`, run
`00c0ebd0-ca95-4da9-be01-e6ae848c82fb`, and route
`8d7483e8-adca-45da-b4f6-9a2b9b0d0cc3` retain the accepted eight-unit plan.
The route selected seven unique specialists, reusing `code-reviewer` for two
review units. Three selected versions were previously governed contractor
hires; no new hire was needed or attempted in this turn.

All eight activation grants were consumed, all eight delegation rows completed,
and all eight native worker rows ended with exit code zero. The Store run is
`completed` with one accepted finalization, while the product host report is
`failed` because its exact collaboration projection is unavailable. Seven
unique specialist-load rows exist for eight units, which is valid plan reuse
but also conflicts with the grader's current unit-count expectation. The first
header is absent, correction count is zero, workspace-write proof is missing,
artifact validation is skipped, and the workspace contains no files. This exact
build and trial must not be rerun.

## Approach

1. Reproduce the captured content-free eight-spawn/eight-wait shape locally,
   including one specialist assigned to two distinct units and the current
   native output schemas.
2. Preserve a bounded invariant code for the exact projection rejection rather
   than collapsing all validator failures into
   `native_collaboration_topology_invalid`.
3. Align unit evidence with the accepted plan: require one exact activation,
   delegation, and worker per unit while allowing one turn-scoped specialist
   load to serve multiple units assigned to the same specialist.
4. Prove that workspace-write units receive their exact goal and authority,
   perform real writes inside only the isolated trial workspace, and create the
   prompt-bound sentinel before artifact grading begins.
5. Keep malformed, conflicting, nested, out-of-scope, missing-child, and
   missing-write evidence fail-closed. Do not weaken the workspace sandbox or
   let the parent/generalist substitute for specialist work.

## Dependencies

AR-218 owns the now-proven four-call planner/recruiter budget. ADR-0124 requires
product grading against the inferred unit graph; ADR-0128 binds every opaque
Codex child to exact plan authority; ADR-0116 requires a real model-authored
workspace sentinel before artifact validation.

## Acceptance

- [ ] A focused fixture reproduces this exact multi-unit topology and identifies
  the first rejected invariant without retaining prompts or child responses.
- [ ] Eight distinct units with seven unique specialists can prove eight exact
  activations, delegations, and workers without requiring eight duplicate
  specialist loads.
- [ ] Invalid native topology and output shapes remain content-free and
  fail-closed with explicit bounded reason codes.
- [ ] Workspace-write units perform real writes only in the exact isolated
  workspace and the model-authored sentinel is independently verified.
- [ ] The first response header is built from accepted Store evidence and any
  correction remains terminal failure.
- [ ] Focused checks, at most two review passes, and the named local fast gate
  pass on one exact head.
- [ ] One next exact build passes autonomous activation and at most one fresh
  README product trial with real artifacts, independent checks, a valid first
  header, and zero corrections.
