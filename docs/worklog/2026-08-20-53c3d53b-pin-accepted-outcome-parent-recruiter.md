---
title: "Worklog detail: Pin accepted-outcome parent recruiter"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [AR-119, AR-252, canary, inference, providers]
related:
  - docs/worklog/README.md
  - docs/decisions/0161-pin-accepted-outcome-parent-recruiter-separately.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
supersedes: []
superseded_by: null
type: worklog
commit: 53c3d53b345d8f8e561437064505caa22476c493
short: 53c3d53b
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
---

# Worklog detail: Pin accepted-outcome parent recruiter

## Purpose

The second exact-main Claude accepted-outcome draw live-proved the indivisible
Haiku planner repair, then stopped at the already documented intermittent
Sonnet recruiter contract failure. The owner chose to isolate that variable
without changing ordinary Claude turns or spending another unchanged draw.

## Approach

The change adds a typed per-host pin for the accepted-outcome parent recruiter,
resolves it to one exact CLI provider during production canary preparation,
projects its identity and bounded cross-provider credentials only into the
disposable accepted-outcome environment, and consumes it only for the primary
recruiter route and its funded repair. Requested parent recruiter and child
judge identities remain distinct report fields. Configuration, README,
changelog, threat model, ADR, and recovery records describe the same boundary.

## Challenges encountered

The repository's broad configuration test still contains one historical
assertion for the old `fast` workforce default even though the committed
default has been `strict` since 2026-08-04. The affected configuration set was
rerun with that unrelated assertion deselected; no production behavior was
changed to satisfy stale history. Restricted execution also required the
repository's host-attested private pytest scratch rather than sandbox scratch.

## Decisions and alternatives

[ADR-0161](../decisions/0161-pin-accepted-outcome-parent-recruiter-separately.md)
records the durable decision. It rejects a general Claude recruiter-route
change, implicit reuse of the child-judge map, a workstation-specific profile
alias, and an unchanged Sonnet retry.

## Verification

- Bounded configuration and canary set: 137 passed, 4 skipped, 1 unrelated
  historical assertion deselected.
- Host-canary and workforce inference/profile set: 152 passed.
- Native-child, activation-canary, cohesion, and host-hook noninterference:
  182 passed.
- Warning-strict Python production spine: 797 passed, 20 skipped.
- Exact final tree: Ruff check and format green; documentation validation green
  for 713 Markdown files; 12/12 fast local gates passed in 1.2 minutes.

No provider call, owner-config mutation, install, hosted workflow, or slow
14-gate harness was run.

## Follow-ups

- [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md): after fresh
  authorization, publish a clean rollup, configure the parent pin, install from
  exact merged main, and run one bounded falsification draw.
- [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md): only
  host-authored producer/verifier evidence may advance accepted-outcome and
  automatic-promotion proof.
