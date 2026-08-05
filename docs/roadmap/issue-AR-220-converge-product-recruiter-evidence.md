---
title: "AR-220: Make product gap hiring evidence converge"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, inference, workforce, hiring, evidence, multi-harness]
related:
  - README.md
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/evals/decision_conformance.py
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
  - tests/test_workforce_inference.py
  - tests/test_workforce_dynamic_hiring.py
  - docs/analysis/2026-08-01-ar-219-readme-story-evidence.html
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
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
blocks: [AR-203, AR-204, AR-219, AR-221]
---

# AR-220: Make product gap hiring evidence converge

## Problem

Exact merged build `5c45f154e720f1c91d2fa7c297c804cbd9c26d0c` passes
default installation and autonomous Codex activation. Its one governed
`python-cli-service` product trial applies both planner and recruiter inference
responses, then fails atomic preflight without publishing a route.

The recruiter validly declares an uncovered unit and the staffing verifier
admits that gap to the governed hiring path. Dynamic contractor hiring then
terminates rejected with content-free hiring-critic reasons
`relationships_not_coherent`, `acceptance_evidence_insufficient`, and
`gap_not_independently_proven`. Staffing remains `no_safe_sufficient_team` plus
`recruiter_abstained`. No specialist, contractor, delegation, header, write, or
artifact is published even though this ordinary application should be
staffable from the inference-designed contractor pool.

## Current state

Trial `ar219-5c45f15-readme-01` is consumed and terminal `NO-GO` after 167.8
seconds. Session `019fbdbd-94a8-7812-a0df-37a28369eeeb`, trace
`019fbdbd-9553-7fb3-8fbd-0b7d9755443f`, run
`03ac1e0c-39b4-4212-ada3-a17bfa911070`, and failure
`82513b21-6dd5-4b64-9adb-27aebede349d` retain the exact content-free boundary.
Planner and recruiter provider attempts were both applied through
`codex-subscription/gpt-5.6-luna`. Atomic preflight retains the terminal hiring
reason codes but intentionally does not publish rejected contractor documents
or claim uncommitted hiring-model receipts.

Cardinalities are one trace, one run, and one preflight failure with zero
routes, plans, loads, grants, consumptions, delegations, workers, or
finalizations. The first header is absent, correction count is zero, isolated
workspace trust and autonomous bypass are proven without persistent changes,
and the exact workspace is empty.

The focused repair uses the exact product prompt and exact three terminal
reason classes against a representative typed gap. Atomic failure evidence did
not retain the rejected candidate or its private inferred work unit, so the
fixture does not claim to reconstruct either. It proves that a replacement
receives bounded typed requirements, live eligibility exclusions, uncovered
coverage, and reason-family guidance while inference still authors the entire
specialist contract. The hiring file is 37/37 green and three new curated
mutations are independently killed with unchanged source.

PR 226 merged the repair as exact
`ff39761c48564f1ace92d346cbe45df64fb86114`. Two bounded reviews, 37 focused
tests, the 656-test named Python spine with six skips, all 110 dashboard tests,
all 39 routing gates, and all 81 decision mutations pass with zero survivors or
invalid cases and unchanged source. Default installation and autonomous
activation pass. Trial `ar220-ff39761-readme-01` accepts and executes seven
units, but no `agent_hiring_cases` row exists: it selected two existing
contractor versions and did not exercise the repaired four-call path. AR-220 is
locally proven but remains live-unproven; AR-221 owns the later wait and empty
workspace failures.

## Approach

1. Reproduce the exact product request and three-class hiring-critic rejection
   in one focused fixture with a representative typed gap; do not claim
   unrecoverable rejected content is exact.
2. Trace which governed gap projection or replacement-hire instruction
   withholds relationship, acceptance, or independent-gap evidence.
3. Repair only that gap-hiring boundary. Inference remains responsible for
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

- [x] A focused product-request fixture reproduces all three content-free
  hiring-critic reasons without storing or inventing provider content.
- [x] A safe inference-designed contractor repair converges locally
  without deterministic specialist selection or parent/generalist fallback.
- [x] Incoherent relationships, insufficient acceptance evidence, unproven
  gaps, unsafe authority, and impossible teams still abstain atomically.
- [x] Curated mutations independently reintroduce each live defect and every
  mutation is killed with unchanged source.
- [x] Two bounded review passes, focused tests, and the named local fast gate
  pass on one exact head.
- [ ] **codex**: One fresh exact-build product trial passes with zero corrections.
- [ ] **zcode**: One fresh exact-build product trial passes with zero corrections.
- [ ] **claude**: One fresh exact-build product trial passes with zero corrections.
- [ ] **hermes**: One fresh exact-build product trial passes with zero corrections.
- [ ] **openclaw**: One fresh exact-build product trial passes with zero corrections.

## Harness scope

This issue's concept applies across all supported execution hosts (codex,
claude, zcode, hermes, openclaw). The shared code path lives in
`agency_runtime/core/workforce/inference.py`,
`agency_runtime/core/workforce/staffing_verifier.py`, and
`agency_runtime/core/workforce/hiring.py` (gap hiring evidence converged
identically for every host), while per-host trial execution is routed through
`agency_runtime/adapters/hooks.py` (codex/claude/zcode via HookBridge) and
`agency_runtime/adapters/base.py` (hermes/openclaw via BaseAdapter). Each host's
live-trial checkbox above is independent.
