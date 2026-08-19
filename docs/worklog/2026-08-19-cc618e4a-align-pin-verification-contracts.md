---
title: "Worklog detail: align pin verification contracts"
status: active
category: worklog
created: 2026-08-19
updated: 2026-08-19
tags: [canary, inference, providers, verification, testing]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_host_canary.py
supersedes: []
superseded_by: null
type: worklog
commit: cc618e4a86a2414c76c1c1157c2d7b6f16c6741d
short: cc618e4a
date: 2026-08-19
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
---

# Worklog detail: align pin verification contracts

## Purpose

Broader verification found two source-coupled fixtures that still represented
the pre-pin contract, plus one artificial one-second setup deadline that could
expire under full-suite load. The runtime pin remained correct; its exact
verification surfaces needed to move with it.

## Approach

The Agency-mode Claude backend fixture now supplies a real config path with an
exact same-transport provider pin and passes that provider, transport, and auth
source to the backend. The decision-conformance mutation still weakens the
successful-route field check adversarially, but its exact source anchor now
recognizes both governed shapes: historical unpinned evidence and new pinned
evidence.

The Codex setup-failure test keeps its original behavioral assertion of one
failed setup call and no model invocation. Only its total deadline changed from
one second to 30 seconds, matching the adjacent setup test and removing a
machine-load race; no production timeout changed.

## Challenges encountered

The first full-gate pass stopped at the intentionally exact mutation anchor.
After that was aligned, the attached run cleared gates 1 through 11 but exposed
the one-second test race in the production spine. The node passed alone before
the deadline edit, confirming timing rather than a pin-path failure. A prior
detached runner's final handle was lost, so no verdict relies on that run.

## Decisions and alternatives

The runtime validator was not loosened and the canary pin was not made optional
in Agency-mode preparation. Test fixtures now carry the same inputs production
requires. The mutation remains a real exactness test rather than being removed
or broadened to a non-source-coupled assertion.

## Verification

- All gate contracts 1 through 11 passed in the attached local runner,
  including 161 workflow-contract tests and all 151 mutation anchors.
- The exact production spine passed 794 tests with 20 expected skips.
- The exact AR-119 matrix-evidence suite passed 670 tests.
- The dashboard gate passed 134 tests at 96.80% line, 86.80% branch, and
  95.49% function coverage.
- The two directly affected canary nodes passed together.
- Documentation metadata, policy availability, documentation contracts, Ruff
  lint/format, and diff checks passed after the final documentation update.

## Follow-ups

- Obtain renewed authorization before installing, changing the owner profile,
  pushing, opening a PR, or running a live canary.
- A fresh host-authored Rule-4 artifact remains required. This verification
  alignment moves no AR-119 matrix cell.
