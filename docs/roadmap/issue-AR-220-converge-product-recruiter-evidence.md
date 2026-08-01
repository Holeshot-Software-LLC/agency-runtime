---
title: "AR-220: Make product recruiter evidence converge"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, inference, workforce, hiring, evidence]
related:
  - README.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_workforce_inference.py
  - tests/test_workforce_dynamic_hiring.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-220
priority: p0
tracker_url: pending authorization
depends_on: [AR-218]
blocks: [AR-203, AR-204, AR-219]
---

# AR-220: Make product recruiter evidence converge

## Problem

Exact merged build `5c45f154e720f1c91d2fa7c297c804cbd9c26d0c` passes
default installation and autonomous Codex activation. Its one governed
`python-cli-service` product trial applies both planner and recruiter inference
responses, then fails atomic preflight without publishing a route.

The recruiter abstains with content-free reasons
`relationships_not_coherent`, `acceptance_evidence_insufficient`, and
`gap_not_independently_proven`. Staffing reports `no_safe_sufficient_team` and
`recruiter_abstained`. No specialist, contractor, delegation, header, write, or
artifact is published even though this ordinary application should be
staffable from the governed roster plus the inference-designed contractor pool.

## Current state

Trial `ar219-5c45f15-readme-01` is consumed and terminal `NO-GO` after 167.8
seconds. Session `019fbdbd-94a8-7812-a0df-37a28369eeeb`, trace
`019fbdbd-9553-7fb3-8fbd-0b7d9755443f`, run
`03ac1e0c-39b4-4212-ada3-a17bfa911070`, and failure
`82513b21-6dd5-4b64-9adb-27aebede349d` retain the exact content-free boundary.
Planner and recruiter provider attempts were both applied through
`codex-subscription/gpt-5.6-luna`.

Cardinalities are one trace, one run, and one preflight failure with zero
routes, plans, loads, grants, consumptions, delegations, workers, or
finalizations. The first header is absent, correction count is zero, isolated
workspace trust and autonomous bypass are proven without persistent changes,
and the exact workspace is empty.

## Approach

1. Reproduce the exact three-class recruiter abstention in one focused fixture
   built from the product scenario's inferred unit and roster-gap evidence.
2. Trace which planner graph, recruiter context, critic result, or projection
   withholds the relationship, acceptance, or independent-gap evidence needed
   for a safe team.
3. Repair only that inference boundary. Inference remains responsible for
   designing every specialist and relationship; deterministic code may verify
   or veto but must not invent a team.
4. Preserve abstention for genuinely incoherent, unsafe, or unevidenced teams,
   and keep atomic publication, external authority, and high-risk approval
   gates unchanged.
5. Add one independent decision mutation for each live rejection class, run at
   most two review passes and the named local fast gate, then permit only one
   new immutable-build activation and at most one product trial.

## Dependencies

AR-218 owns the bounded planner/recruiter inference budget. AR-219 owns the
overall README product proof and remains blocked until this first staffing
boundary converges. Tracker creation is pending explicit outward-write
authorization.

## Acceptance

- [ ] A focused exact-scenario fixture reproduces all three content-free
  recruiter abstention reasons without storing provider content.
- [ ] A safe sufficient team or inference-designed contractor repair converges
  without deterministic specialist selection or parent/generalist fallback.
- [ ] Incoherent relationships, insufficient acceptance evidence, unproven
  gaps, unsafe authority, and impossible teams still abstain atomically.
- [ ] Curated mutations independently reintroduce each live defect and every
  mutation is killed with unchanged source.
- [ ] Two bounded review passes, focused tests, and the named local fast gate
  pass on one exact head.
- [ ] One new exact installed build passes activation and at most one fresh
  product trial with a valid first header, zero corrections, real specialist
  execution, workspace writes, artifacts, and independent acceptance checks.
