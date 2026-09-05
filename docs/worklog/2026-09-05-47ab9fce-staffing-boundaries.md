---
title: "Worklog: preserve gap progress and enforce staffing boundaries"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [staffing, correctness, deadlines]
related:
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/decisions/0217-keep-subject-domains-out-of-execution-authority.md
supersedes: []
superseded_by: null
type: worklog
commit: 47ab9fcebc1fe8106e7f776710db85e4be8c3e54
short: 47ab9fce
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/669
related_issues:
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
---

# Worklog: preserve gap progress and enforce staffing boundaries

## Purpose

Address three independently reproduced staffing failures without inheriting
conclusions from the earlier capsule. This is a recovery checkpoint, not a claim
of installed or live-verified completion.

## Approach

Preserve successful gap assignments while other inference-declared gaps remain
empty; retain nominations on unrelated units during amendment. Bound all route
provider calls and repairs by one absolute monotonic deadline with a terminal
close margin. Treat domains as descriptive retrieval signals, leaving audited
authority, explicit exclusions and substantive requirements as eligibility gates.

## Challenges encountered

Existing tests used domains as proxies for capabilities. Those waiver fixtures
now exercise actual capability gaps; historical domain receipts remain readable.
New deadline checks expose complexity warnings still requiring focused review.

## Decisions and alternatives

ADR-0216 carries the absolute deadline rule. ADR-0217 supersedes the domain veto.
Do not elevate an audited planner to implementation authority or skip critics.
Do not extend the lease to disguise slow providers.

## Verification

The new boundary suites pass 25 tests. Hiring/coverage-gap/shortfall suites pass
104; planner-domain/selection-safety/inference suites pass 130 with one skip.
Metadata, documentation validation and diff whitespace checks pass.
These are deterministic checks with temporary stores, not live provider evidence.

## Follow-ups

AR-400 tracks fast verification, PR merge, install and all-host smoke.
AR-401 needs transport and actual-preflight boundary regressions.
AR-402 needs final safety review. The owner also requested a performance pass:
test fresh-process roster-vector cache reuse without caching user prompts or
changing inference quality.
