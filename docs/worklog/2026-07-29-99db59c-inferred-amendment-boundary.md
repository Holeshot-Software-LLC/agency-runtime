---
title: "Worklog detail: Bind and bound inferred amendments"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [workforce, hiring, amendments, inference, mutation-testing]
related:
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/handoffs/issue-AR-200.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 99db59c
short: 99db59c
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
---

# Worklog detail: Bind and bound inferred amendments

## Purpose

Repair the sole remaining workforce gap from AR-200's first ordinary Codex
canary without reintroducing deterministic online selection. The canary chose a
coherent documentation amendment but collapsed its construction failure into a
generic code, preventing atomic specialist publication.

## Approach

Inference continues to choose whether to amend and the exact existing target.
After that decision, Agency binds the contract identity to the selected worker,
preserves its authority and context checks, and merges every projected list by
retaining all existing values before accepting additions up to the destination
limit. The full employment contract remains unchanged for compilation and
critic evidence. Amendment failures now map to allowlisted content-free stages.

Two new curated mutations remove target-identity binding and restore unbounded
outcome merging. Each must be killed only by its exact focused regression.

## Challenges encountered

The installed canary retained only the generic amendment code by design, so it
could not reveal rejected provider content. A proposed source-level provider
diagnostic was denied because it would transmit the active roster snapshot and
was not retried. A provider-free reproduction first hit the expected untrusted
`C:\tmp` storage boundary, then passed in Agency's owner-private temporary
directory against a copy of the real `technical-writer` record. The live store
remained unchanged.

## Decisions and alternatives

ADR-0081 governs the amendment boundary: inference owns target choice, while
the chosen existing worker owns revision identity, authority, and context.
Silently replacing authority or context was rejected. Unbounded additive lists
were also rejected; the merge retains all existing validated values before
bounded additions and fails later coverage checks if required facts cannot fit.
ADR-0113 governs the expanded mutation proof.

## Verification

- Provider-free real-worker reproduction: `technical-writer` amended in place
  in the private copy, 272 workers before and after, all existing projected
  values preserved, 12 employment outcomes retained, workforce outcomes capped
  at 8, qualifiers capped at 4, and live revision/hash unchanged.
- Focused suite: 111 passed, 1 skipped, 1 expected xfail.
- Named fast Python spine: 661 passed, 6 skipped.
- Dashboard UI: 109 passed.
- Routing evaluation: every correctness, policy, delegation, CLI-startup,
  latency, and 263/1,000/10,000-agent scale gate passed.
- Decision conformance: green baseline; 7 of 7 mutations killed; 0 survivors;
  0 invalid results; source inputs unchanged.
- Documentation: metadata and normal validation passed for 537 Markdown files.
- Ruff lint, Ruff format, and Git diff checks passed.

## Follow-ups

Push and merge the repair PR, exact-install its merge for Codex and ZCode, run
one final bounded ordinary Codex canary, and publish its complete scoped
evidence to the local AR-200 report.
