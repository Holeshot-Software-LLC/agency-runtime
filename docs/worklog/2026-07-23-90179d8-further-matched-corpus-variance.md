---
title: "Worklog detail: Further matched corpus variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, inference, workforce, selection, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
supersedes: []
superseded_by: null
type: worklog
commit: 90179d8b8b9708a2d5077c5e5005004ffa6bc102
short: 90179d8
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Further matched corpus variance

## Purpose

Run the complete 19-case Windows corpus required after both bounded
confidence-abstention cases recovered, while preserving the exact matched
controls and treating malformed upstream arms as validity failures.

## Approach

The run started from clean ledger `160c2dd`. A fail-closed external wrapper
verified the branch and clean state, recorded HEAD, and captured stdout and
stderr before parsing. The unchanged parser verified all 19 canonical cases,
matched controls, arm bindings, aggregate metrics, validity failures, and the
exact projection.

Agency passed 17/19. Application observability abstained on confidence after
its immediately preceding bounded pass, selection-safety review abstained on
margin, and broad application passed. Five upstream arms returned unknown
disabled shadows, making the complete benchmark invalid.

## Challenges encountered

The new failures are not stable across complete or bounded runs. The provider
contract failures also prevent comparative interpretation of the complete
corpus. Neither condition supports a scenario-specific route or a threshold
change.

## Decisions and alternatives

No product or selection-policy change was made. Treating the five malformed
upstream arms as losses and using the aggregate delta as comparative evidence
was rejected. The next bounded package preserves complete outcomes for
application observability and selection-safety review before any semantic
change is considered.

## Verification

- The process returned status 1 in 414.999636 seconds.
- The 1,183,103-byte stdout had SHA-256
  `01ada91b3c40baf34647b9230a23eedd61fbb667cbedb1647a27d3eb601ac831`;
  stderr was empty and independently hash-verified.
- The exact 12,946-byte projection had SHA-256
  `7f8c9634b74eccd44cfca76480246a6e9a87baa6231480ab0e14d0bc92430db8`.
- The projection embedded in AR-119 matched the captured projection byte for
  byte.
- Metadata, policy availability, worklog-current, full docs validation, and
  `git diff --check` passed; docs validation covered 319 Markdown files.

## Follow-ups

- Run one instrumented matched confirmation of application observability and
  selection-safety review.
- Do not advance to contractor lifecycle or claim Agency is better.
