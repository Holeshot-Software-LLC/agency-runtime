---
title: "Worklog detail: Post-pass corpus variance"
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
commit: 518d2272fe5089be60d0cc0612925b6e9f66c20d
short: 518d227
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog detail: Post-pass corpus variance

## Purpose

Preserve the complete corpus immediately after the second 19/19 Agency
observation and identify its exact bounded confirmation package.

## Approach

The unchanged 19-case Windows corpus ran from clean ledger `644aec1` with all
fixed matched controls. Both streams were captured before parsing, and the
exact projection was verified byte-for-byte.

## Challenges encountered

Active incident safely abstained on margin and accounts payable omitted the
required CFO review. Three upstream arms returned unknown disabled shadows, so
the comparison remained invalid.

## Decisions and alternatives

No semantics changed from one variable corpus. The next package confirms both
Agency failures unchanged with complete outcomes preserved. Upstream errors
remain validity failures, never losses.

## Verification

- The process returned status 1 in 441.588810 seconds; 1,189,496-byte stdout
  SHA-256 was
  `c3d5276a257e3ec6fefd7a64ca1c24b1c852ae6ca12853a0c0d48864c7523707`;
  stderr was empty.
- The 12,979-byte projection SHA-256 was
  `72ff44fb13c003221bb623fbeb2d487ad1a170759eb8ff3f9c8fc9dff111524e`
  and matched the canonical issue exactly.
- Agency scored 17/19 with complete disabled disclosure and zero unsafe
  selections; all 38 arms retained exact bindings.
- Metadata, policy, worklog, docs, and diff checks passed.

## Follow-ups

- Instrument active incident and accounts-payable/CFO under unchanged controls.
- Do not claim Agency is better or reinterpret malformed upstream arms.
