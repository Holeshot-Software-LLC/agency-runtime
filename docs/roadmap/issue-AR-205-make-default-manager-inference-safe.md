---
title: "AR-205: Make the default manager inference-safe"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [product, routing, managers, inference, roster]
related:
  - README.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-205
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/190
depends_on: [AR-204]
blocks: []
---

# AR-205: Make the default manager inference-safe

## Problem

Agency treats the imported `agents-orchestrator` and `chief-of-staff` roles as
universal protected resident managers. Their audited contracts are not
universal: one is useful for multi-specialist decomposition and delegation,
while the other is useful for sustained program and executive coordination.
Making both resident on every turn hides that distinction, prevents normal
opt-out, and risks making deterministic residency look like specialist
selection.

The audited roster already carries positive `preferred_when` and negative
`avoid_when` activation criteria, but the primary workforce recruiter receives
only the first two positive qualifiers and no negative criteria. Inference
therefore cannot use the complete bounded activation contract that the hard
staffing verifier later enforces.

## Current state

The resident-manager kernel has a separate, hash-bound parent lifecycle, so it
does not need an ordinary roster worker. The imported manager records remain in
the complete audited roster. Workforce contracts already project
`preferred_when` to `scope_qualifiers` and `avoid_when` to `not_for`, and the
staffing verifier rejects exact negative matches. The missing boundary is the
resident identity and the recruiter-card projection.

## Approach

1. Replace the two imported resident identities with one Agency-native,
   parent-only `agency-steward` kernel that owns the user contract, inference
   receipt boundary, evidence lifecycle, and fail-loud completion boundary.
2. Keep `agency-steward` outside the selectable roster. It never selects,
   ranks, schedules, executes, or claims specialist work.
3. Return `agents-orchestrator` and `chief-of-staff` to the ordinary installed
   roster so valid inference may select them for their audited scopes and an
   owner may disable either one.
4. Remove the legacy deterministic no-match worker fallback. A substantive
   turn without a valid inference staffing decision selects nobody; the
   resident steward remains parent context, not a selected specialist.
5. Send all four bounded positive and negative activation criteria to the
   recruiter, and retain deterministic verification as a reject-only safety
   boundary.
6. Enforce a no-generalist completion gate. Every substantive question or
   action must carry an accepted specialist staffing receipt. When inference
   proves a roster gap, the hiring stage defines and creates a narrow contractor
   for that work unit, then restaffs and verifies the result before the turn may
   proceed. The role may be as small as an evidence-bounded expert in the
   missing domain; it does not need to be a predeclared universal persona.
7. Treat workforce design as an open-ended specialist pool. For each unit,
   inference first defines who an exacting owner would want handling it, then
   selects a roster worker only when that worker faithfully matches the ideal.
   The installed roster is a reusable cache of specialists, not the boundary of
   possible expertise.

## Dependencies

ADR-0118 remains the authority contract for specialist staffing. AR-204 owns
the exact installed product proof and final README-story acceptance.

## Current evidence

- Source routing defines the ideal role before roster comparison, accepts an
  explicit zero-candidate gap, creates a distinct narrow contractor for an
  ordinary task gap, and blocks substantive preflight when the accepted route
  is empty either before or after isolated child-plan normalization.
- The resident contract is the singleton `agency-steward`; the imported
  orchestrator and Chief of Staff remain audited, disableable roster workers.
- Focused warning-strict evidence is green: 166 core routing/workforce tests,
  30 preflight-boundary tests, 94 native-hook tests, 48 adapter-parity tests,
  27 header/store tests, and 64 MCP/ZCode/Claude tests with five intentional
  skips. The dashboard client remains green at 110 tests. The HTTP surface
  passed 98 tests with three intentional skips before its sole stale assertion
  was corrected and reverified directly.
- Ruff checks all Python sources, tests, and scripts cleanly. Four new curated
  decision mutations have current unique anchors and their named tests pass;
  the complete decision-conformance run and named fast spine remain pending.
- No exact installed Codex trial has been attempted for this source package.

## Acceptance

- [x] Every Agency-enabled parent turn binds exactly one resident
  `agency-steward` kernel.
- [x] `agency-steward` cannot appear as a selected or delegated specialist.
- [x] `agents-orchestrator` and `chief-of-staff` remain installed, are
  disableable, and appear only through valid inference selection evidence.
- [x] Deterministic no-match routing cannot select a resident or specialist.
- [x] Recruiter cards carry the complete bounded `scope_qualifiers` and
  `not_for` activation contract.
- [x] Exact negative activation criteria remain reject-only hard verification
  and can produce a visible staffing gap.
- [x] Every substantive ask has an accepted roster specialist or inference-
  created contractor; a resident-only/generalist answer is a terminal failure.
- [x] An arbitrary novel-domain gap can create a narrow task-scoped contractor
  without a deterministic keyword or pre-created-agent rule.
- [x] Recruiter inference reasons ideal-role-first against an open-ended pool
  and never selects a merely least-wrong generalist.
- [ ] Focused tests, the named fast spine, decision mutations, and the exact
  installed product trial pass with zero response corrections.
