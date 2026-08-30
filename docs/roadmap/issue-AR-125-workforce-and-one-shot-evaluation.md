---
title: "AR-125: Prove workforce selection, host portability, and Agency-on/off value"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-08-12
tags: [evaluation, testing, portability, routing]
related:
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
