---
title: "AR-202: Make recruiter repair converge across invalid units"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [workforce, inference, recruiter, repair, diagnostics, routing]
related:
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/decisions/0115-aggregate-bounded-recruiter-repair-failures.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/handoffs/issue-AR-202.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-202
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/182
depends_on: [AR-201]
blocks: [AR-200]
---

# AR-202: Make recruiter repair converge across invalid units

## Problem

AR-201 restored the promised third fast-mode provider call, but ordinary trial
`ar201-ed4450e-ordinary-01` still produced no workforce. The planner response
applied, then both the recruiter response and its one bounded repair were
rejected as `provider_response_contract_invalid`. The exact route evaluated
272 workers, retained 53 eligible workers, planned nine units, and correctly
abstained instead of inventing a deterministic team.

The recruiter transport schema passed on both rejected calls. The semantic
parser currently raises the first failing invariant, so a broad response can
receive feedback for only one invalid unit or condition. A repair that fixes
that first condition can expose a second one after the final allowed call. The
durable receipt then retains only the generic rejection family, which proves
failure but cannot distinguish multi-unit non-convergence from a repeated
single-unit error.

## Current state

Fresh fast mode now funds planner, recruiter, and one recruiter repair. The
live trace proves all three calls were made through the configured
`codex-subscription` wrapper using requested and resolved model
`gpt-5.6-luna`: one receipt succeeded and two failed. Route latency was
114.200 seconds. The route ended `abstained` with zero selected, loaded, or
delegated specialists and no hiring attempt.

The implementation now collects an ordered allowlisted failure set across all
planned units. Its same-provider accumulator removes failed rows, preserves
valid rows, and reconstructs a repaired proposal in exact plan order without
adding or promoting a candidate. The production-shaped nine-unit regression
repairs two independently invalid unit decisions in one bounded call.

Focused runtime review passes 85 tests. Decision conformance passes a green
baseline and kills all 13 curated mutations, including first-error-only
recruiter validation, with zero survivors or invalid results and unchanged
source inputs. The named fast production spine, merge, install, and final
ordinary canary remain pending.

## Approach

1. Represent recruiter semantic failures as a bounded, content-free set keyed
   by planned unit and allowlisted invariant code; never persist provider text
   or an unknown candidate identifier.
2. Validate all supplied unit rows before rejecting the response so one repair
   prompt receives every discovered semantic failure, not only the first.
3. Preserve already validated rows in the same-provider accumulator and allow
   the repair response to replace only failed rows.
4. Keep inference authoritative: deterministic code may validate, reject, and
   merge corrected rows but may not add, reorder, or promote a specialist.
5. Add a broad multi-unit regression and a decision-conformance mutation that
   restores first-error-only behavior.
6. Run focused review and the named fast gate before merge and exact
   Codex/ZCode installation. Do not spend another ordinary canary until the
   AR-203 product-harness boundary is also repaired.

## Dependencies

AR-201 owns the reachable three-call default. ADR-0088 preserves the strict
configured-provider inference boundary. ADR-0113 owns mutation evidence, and
ADR-0114 limits fast mode to one bounded semantic repair.

## Acceptance

- [x] Recruiter semantic rejection exposes only bounded allowlisted unit and
  invariant codes; provider-authored content and unknown identifiers are never
  persisted.
- [x] One response containing at least two independently invalid unit decisions
  reports both failures in the first rejection.
- [x] One same-provider partial repair can replace every rejected row while
  preserving already validated rows and exact plan order.
- [x] Deterministic verification never adds, reorders, or promotes an online
  specialist while producing the complete failure set.
- [x] A broad nine-unit production-shaped regression fails under first-error
  behavior and passes with one bounded repair.
- [x] The decision-conformance gate kills an exact mutation that restores
  first-error-only recruiter validation.
- [ ] Focused tests and the named fast production gate pass on the exact source
  revision.
- [ ] The merged revision is exact-installed for Codex and ZCode before the
  next ordinary canary.
