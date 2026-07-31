---
title: "Worklog detail: Align inferred plans with safety policy"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [workforce, inference, routing, evaluation, product]
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
commit: 38e7e1c
short: 38e7e1c
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Align inferred plans with safety policy

## Purpose

Repair the first causal preflight boundary from exact-build product trial
`ar205-cc32238-readme-01`: inference was asked to author a looser plan than the
deterministic safety validator accepted, and recruiter inference lacked exact
typed evidence for distinguishing a safe roster team from a real hiring gap.

## Approach

Expose the deterministic plan vetoes as a structured acceptance contract and
bounded repair guidance, while requiring inference to author every plan unit and
dependency. Expose deterministic, non-ranked typed requirements, candidate
coverage, execution eligibility, and uncovered requirements to recruiter
inference, while retaining model ownership of ranking, selection, and gap
declaration. Align compact schema capacity with the configured 16-unit bound,
normalize install/deploy/release language emitted by planner prose, and remove a
redundant generic communication requirement from documentation artifacts.

## Challenges encountered

The original product report projected `route_not_found`, but the exact matching
session proved `preflight_failed`. Direct provider replay then exposed two
sequential semantic failures: contradictory assurance instructions at planning,
followed by insufficient typed evidence at recruitment. A strengthened release
test caught that plural and past-tense planner language did not match the
singular policy token set before commit.

## Decisions and alternatives

Deterministic code remains reject-only. It may describe acceptance constraints,
recall coverage facts, and veto unsafe output; it may not synthesize missing
units, rank workers, pick a nearest match, or silently turn invalid inference
into a deterministic plan. The roster remains a cache, and a nonempty uncovered
requirement is presented to inference as evidence for a distinct contractor gap.

## Verification

- A real provider replay accepted a nine-unit plan and nine specialist
  assignments with no staffing abstention.
- Focused final-boundary verification passed 127 tests with one intentional
  skip; the narrower planner/recruiter suite passed 84 tests.
- The named warning-strict fast spine passed 636 tests with six intentional
  skips on the final committed source.
- Dashboard UI passed 110 tests, routing evaluation 1.4.0 passed every gate,
  documentation validated 571 files, and all 602 Python inputs were
  format-current.
- The 44-mutation evaluator passed before the final release-language
  normalization; the exact committed-tree rerun is the first post-checkpoint
  gate required by context telemetry.

## Follow-ups

Run exact-tree decision conformance, publish and review the branch, install the
exact merge for Codex, ZCode, and dashboard, and consume one fresh exact-build
product trial. Generate the local evidence page and OpenClaw handoff only after
that trial records zero corrections and full product evidence.
