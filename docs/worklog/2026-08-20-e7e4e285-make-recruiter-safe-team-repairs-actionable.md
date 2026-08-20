---
title: "Worklog detail: Make recruiter safe-team repairs actionable"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [AR-119, AR-253, recruiter, inference, diagnostics]
related:
  - docs/worklog/README.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
supersedes: []
superseded_by: null
type: worklog
commit: e7e4e2858f761fb898fce4b17a147c3655b0ec17
short: e7e4e285
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
---

# Worklog detail: Make recruiter safe-team repairs actionable

## Purpose

The first accepted-outcome draw after the isolated parent-recruiter pin reached
the requested Codex subscription provider twice, but both recruiter responses
were rejected `staff_without_safe_team`. The surviving receipt proved that
provider routing worked and exposed an underspecified recruiter classification
and repair contract instead.

## Approach

The recruiter prompt and machine response contract now say that every
`required` candidate is mandatory and consumes a slot, `acceptable` candidates
are optional alternatives or complements, and `forbidden` candidates are
excluded. When the verifier rejects a staff row, its one funded repair receives
bounded deterministic facts: the effective required and team-search sets,
available complement slots, exact missing requirements, and candidate coverage.
The runtime does not propose a replacement team.

Future durable failure receipts add only the three content-free counts proposed
in AR-253: required, ranked executable, and maximum selected. The projection
accepts legacy rows and rejects partial or malformed count triples. Diagnostic
axis calculation no longer credits a candidate the recruiter declared
forbidden, while post-eligibility exclusions remain unchanged for team building.

## Challenges encountered

The completed canary did not persist either raw recruiter JSON body or the
applied planner document, so the byte-exact dynamic recruiter prompt could not
be reconstructed. The diagnostic package preserves that limit and records only
the Store's allowlisted projections, exact actual provider attempts, and the
source-defined prompt shape. A widened non-governing suite also retains one
unrelated pre-existing failure: a configuration transaction test omits the
required keyword-only `narrow` argument.

## Decisions and alternatives

This package fixes the unsafe-team output contract rather than changing
provider order, the accepted-outcome parent pin, the child-judge pin, ordinary
turn routing, or the deterministic team builder. It rejects provider retries,
locally selected replacement teams, and reconstructed model prose as evidence.
[ADR-0118](../decisions/0118-require-inference-owned-staffing.md) remains the
staffing authority; [ADR-0132](../decisions/0132-fund-one-repair-per-workforce-inference-stage.md)
still permits exactly one bounded recruiter repair.

## Verification

- Focused recruiter, receipt, and decision-conformance tests: 97 passed with
  warnings as errors.
- Warning-strict production spine: 797 passed, 20 skipped.
- Deterministic AR-119 matrix regression suite: 695 passed.
- Ruff check/format, documentation metadata, policy availability, and
  documentation contracts passed before the ledger update.
- Full local harness: all 14 gates passed in 13.9 minutes, including 161
  workflow-contract tests, 151 current mutation anchors, the production spine,
  the AR-119 matrix suite, and 134 dashboard UI tests with coverage thresholds.

No provider, host CLI, Store write, owner-config mutation, install, push, hosted
workflow, or live retry ran in this package.

## Follow-ups

- [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md): after fresh
  publication, install, config, and one-draw authority, falsify the repair with
  one exact-main accepted-outcome draw.
- [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md):
  retain future count-bearing red receipts and measure repeated valid staffing
  outcomes without treating a single green or red draw as a rate claim.
