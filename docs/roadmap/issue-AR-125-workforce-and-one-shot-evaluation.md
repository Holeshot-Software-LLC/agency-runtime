---
title: "AR-125: Prove workforce selection, host portability, and Agency-on/off value"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-09-05
tags: [evaluation, testing, portability, routing]
related:
  - docs/roadmap/handoffs/issue-AR-125.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/decisions/0222-retire-superseded-live-routing-contract.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-125
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/138
depends_on: [AR-120, AR-121, AR-122, AR-123, AR-124, AR-179]
blocks: [AR-119]
---

# AR-125: Prove workforce selection, host portability, and Agency-on/off value

## Problem

Selection activity and unit tests do not prove that Agency assembles correct
teams, improves matched outcomes, or runs portably through every supported host.

## Current state

AR-115 retirement note (2026-09-05): ADR-0222 removes its obsolete heuristic/
six-field-header design, not the need for configured, forbidden-selection and
current-host evidence. Those live/evaluation obligations remain here and under
AR-119. No old or current unstaffed/unverified session is counted as success.

**Oldest-first disposition: retain open.** At reviewed main `bc392228`,
the evaluator and safety checks exist, but their presence is not a matched
value result. Fresh local comparison/selection/upstream/full-roster regression
package: 33 passed in 2.68s, including identical-binding and malformed-arm
validity checks. These are deterministic fixture tests, not live configured-
inference, held-out or Agency-on/off outcome trials. The canonical AR-119
matrix still records matched value as unproven.

The three checked criteria below are historical receipts, including the exact
Windows/Linux candidate `29da6eca`; this reconciliation does not recertify them
for today's install or mark the three open criteria satisfied. The September
AR-348 installed smoke is deterministic, not five host-authored live canaries.
The current unverified session likewise supplies no positive evidence.
ADR-0102 already moved complete one-shot applications to AR-178; do not restore
that expensive corpus as a prerequisite or retire the still-relevant matched
selection/value requirements with it. Keep tracker #138 open.

### Historical candidate checkpoint

Every-worker semantic cases and pairwise/lifecycle-team properties are green.
Exact candidate `29da6eca` now has clean Windows/Linux artifacts, fresh wheel
and source installs, and a verified merged release set. Configured-inference
and held-out matched evidence, paired Agency-on/off value, normal-profile
installation, and five live host canaries remain open. Complete one-shot
applications moved to non-blocking post-production AR-178. AR-179 repaired the
live false-sufficient-team defect for named regulated assurance work and passed
a fresh fail-closed confirmation. Those bounded results do not complete the
broader matched outcome or five-host evidence here.

## Approach

Complete independent per-worker semantic cases, pairwise composition properties,
meaningful lifecycle teams, configured-inference and held-out matched-selection
corpora, paired Agency-on/off trials, installed artifacts, and five-host
contracts for Codex, Claude, Hermes, OpenClaw, and ZCode. Keep complete-
application evaluation in AR-178 without weakening matched controls.

Current remaining sequence:

1. Pin one source/install/roster/configuration identity and record which
   configured evaluator/host boundaries are actually usable. Missing provider
   credentials or attended hook trust are explicit operator holds, not retries.
2. Collect the bounded configured and held-out matched-selection evidence;
   retain malformed/timed-out arms as invalid and record zero forbidden,
   ineligible or incompatible selections before any success claim.
3. Collect paired Agency-on/off outcomes with identical controls, exact-version
   participation and independent grading; do not infer value from usage or
   passing fixture tests. Then join each supported host's exact live artifacts
   to the canonical matrix. Windows execution stays with the owner.

Under the owner's backlog-reconciliation-first order, publish this disposition
and inspect AR-127 next. The live study remains owned here; no duplicate issue,
new acceptance waiver, current-version portability claim or hosted dispatch.

## Dependencies

All preceding AR-119 slices provide the behavior this evidence must grade.

## Acceptance

- [x] Every worker passes positive, hard-negative, qualifier, shadow, and
  eligibility cases.
- [x] Pairwise invariants and curated lifecycle teams pass.
- [ ] Configured-inference and held-out matched-selection corpora produce
  complete comparable evidence with zero forbidden, ineligible, or conflict
  regressions; malformed or timed-out arms remain validity failures.
- [ ] Matched Agency-on/off trials prove accepted exact-version specialist
  participation and independently graded outcome lift for the same ask, host,
  model, configuration, and evaluator.
- [x] Exact candidate Windows/Linux installed artifacts pass smoke, portability,
  and release verification.
- [ ] Codex, Claude, Hermes, OpenClaw, and ZCode contracts and live canaries pass.
