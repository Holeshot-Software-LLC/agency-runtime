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
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/hiring_contract.py
  - tests/test_codex_activation_canary.py
  - tests/test_product_one_shot.py
  - tests/test_workforce_dynamic_hiring.py
  - tests/test_workforce_hiring_contract.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-218-fund-one-repair-per-inference-stage.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0133-treat-product-specialist-loads-as-turn-scoped.md
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

The repaired exact build reaches a different first boundary. Its activation is
green, but its one product trial fails atomically while filling an
inference-declared workforce gap: a governed contractor proposal is classified
as high risk and therefore cannot commit without human approval. No route or
specialist execution is published from that failed preflight.

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

PR 223 merged the repair as exact commit
`386afca23bdc16e6c49c6dab55967b26a902a5b2`; package
`0.1.0+g386afca23bdc` is installed from that immutable revision. Bare install
selected Codex, ZCode, and dashboard. The dashboard is active and reachable,
ZCode is registered and enabled, and Codex is registered and runtime-verified.

Autonomous activation passed once in session
`019fbd75-2ea2-7f80-b6f7-eb2bb0724f2a`, trace
`019fbd75-3d0b-7b10-a463-2b95ee1fe2ab`, run
`36b9b721-7efa-400d-9e07-ba1b860a1772`, and route
`337566cc-2adc-435e-960a-ac09e6a45e71`. Inference selected
`code-reviewer`; one native child completed; the first header was valid; the
correction count was zero; autonomous hook bypass was proven; and no persistent
profile change occurred.

Trial `ar219-386afca-readme-01` is consumed and terminal `NO-GO` after 160.9
seconds. Session `019fbd7a-0c24-7581-a49d-91bbe870f7ea`, trace
`019fbd7a-0cb8-7dc0-ba1b-415d3d834a3e`, and run
`6e03910a-ec8b-4c4a-8d15-f2700b7cd219` retain one atomic preflight failure.
Planner and recruiter structured responses were applied, then dynamic gap
hiring returned `high_risk_human_approval_required`; staffing ended with
`no_safe_sufficient_team` and `recruiter_abstained`. Cardinalities prove zero
routes, loads, grants, delegations, workers, or finalizations. Exact isolated
workspace trust and autonomous hook bypass passed without persistent changes,
but the first header was absent, workspace-write proof was missing, validation
was skipped, correction count was zero, and the workspace remained empty.

The merged topology repair treats a specialist load as turn-scoped by slug
and rejects reuse unless every correlated unit grant has the same immutable
version and prompt hash. It preserves the first exact product-projector failure
as an allowlisted content-free code without masking a more basic missing-spawn
or missing-wait diagnosis. Parent plan rows include verified mutation scope;
the first delegated `workspace_write` child owns the prompt-bound sentinel; and
each opaque child is told explicitly to execute its decrypted native message as
the exact work-unit goal.

Both bounded review passes are complete. The focused suite passes 102 tests.
The named Python spine passes 643 tests with six skips, the dashboard passes all
110 tests, all 39 routing gates pass, documentation and Ruff validation are
clean, and the exact changed-source decision slice kills 22/22 mutations with
zero survivors or invalid results and `source_unchanged=true`. The full
73-mutation process completed after its outer shell deadline, but its terminal
JSON was not retained; it is not claimed as a fresh exact-head pass. No new live
attempt is permitted on `386afca`.

Atomic preflight intentionally did not persist the rejected contractor
document, so the exact triggering risk class is not recoverable from the Store.
Code inspection identifies two authority bugs that can independently produce
this receipt: the model supplies `external_mutation` instead of the validated
work unit, and substring classification can treat negated requirements such as
`no credential access` as positive credential authority. The next package is
limited to those two fail-closed invariants and content-free risk diagnostics.

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
6. Make the validated work unit authoritative for contractor mutation scope,
   reject positive high-risk authority without approval, and prevent explicit
   negated safety constraints from being classified as granted authority.

## Dependencies

AR-218 owns the now-proven four-call planner/recruiter budget. ADR-0124 requires
product grading against the inferred unit graph; ADR-0128 binds every opaque
Codex child to exact plan authority; ADR-0116 requires a real model-authored
workspace sentinel before artifact validation.

## Acceptance

- [x] A focused fixture reproduces this exact multi-unit topology and identifies
  the first rejected invariant without retaining prompts or child responses.
- [x] Eight distinct units with seven unique specialists can prove eight exact
  activations, delegations, and workers without requiring eight duplicate
  specialist loads.
- [x] Invalid native topology and output shapes remain content-free and
  fail-closed with explicit bounded reason codes.
- [ ] Workspace-write units perform real writes only in the exact isolated
  workspace and the model-authored sentinel is independently verified.
- [x] The first response header is built from accepted Store evidence and any
  correction remains terminal failure.
- [ ] A workspace-local contractor remains standard-risk when it only carries
  negated credential/external safety constraints, while genuine external,
  credential, destructive, medical, legal, and financial authority remains
  approval-gated.
- [ ] Focused checks, at most two review passes, and the named local fast gate
  pass on one exact head.
- [ ] One next exact build passes autonomous activation and at most one fresh
  README product trial with real artifacts, independent checks, a valid first
  header, and zero corrections.
