---
title: "Worklog detail: Close final review safety gaps"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [workforce, inference, routing, safety, review, scale]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 81b887f
short: 81b887f
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/192
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Close final review safety gaps

## Purpose

Resolve all four valid P1 findings from PR 192's second and final broad Codex
review without reopening deterministic planning or selection.

## Approach

Clamp only the compact planner parser to its 16-unit schema ceiling while
retaining the configured downstream staffing budget. Bound per-unit typed
recall to 24 stable, coverage-first, non-ranked candidate evidence rows while
computing exact candidate counts and uncovered requirements over the complete
eligible roster. Require positive verification language to be grammatically
scoped to each requested release operation. Apply third-person negation removal
only to evidence outcomes, preserving standards named in remediation requests.

## Challenges encountered

An initial bounded recall sample could preserve one candidate per requirement
yet omit the installed worker that covered the entire architecture unit. The
final recall includes full-coverage eligible contracts first, then stable
per-requirement representatives and stable filler rows. This remains retrieval,
not ranking or selection. The stricter release grammar also had to retain the
repository's canonical multi-operation generated evidence while rejecting
phrases that verify test results merely before deployment.

## Decisions and alternatives

No third broad review pass is added after the two package review passes. Every
second-pass P1 has a direct regression and the existing wider safety suite is
green. The roster remains available to inference through all detail cards; the
typed matrix is bounded evidence, and omission from that matrix is explicitly
not an exclusion from recruitment.

## Verification

- Seven focused cases covering the four P1s pass.
- Both complete affected modules pass 83 tests with warnings as errors.
- Routing correctness, workforce selection and hiring, and decision-conformance
  tests pass 115 cases with one intentional skip.
- The 16-unit by 500-candidate recall regression retains exact full-roster
  counts, caps each row at 24, and remains below 320 KiB.
- Ruff check and formatting pass all touched Python files.
- Documentation metadata and validation pass 573 Markdown files; diff integrity
  is clean.
- On the final committed tree, the named fast spine passes 636 tests with 6
  intentional skips, the dashboard passes 110 tests, Ruff checks and formats
  all 602 Python files, and documentation validation passes 574 Markdown files.
- Routing evaluation 1.4.0 passes every gate. Decision conformance passes its
  baseline, kills 44/44 mutations in 327.7 seconds, records no survivor or
  invalid mutation, and leaves the source tree unchanged.
- All seven comments from the two bounded PR review passes have repair replies,
  and every review thread is resolved.

## Follow-ups

Merge and exact-install PR 192, then consume the one fresh product trial.
Generate the local evidence page and OpenClaw handoff from recorded trial
evidence only.
