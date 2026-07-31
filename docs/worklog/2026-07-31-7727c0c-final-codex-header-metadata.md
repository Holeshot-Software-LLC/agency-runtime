---
title: "Worklog detail: Bound final Codex header metadata"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [hooks, codex, headers, preflight, utf8, review]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0123-use-general-preflight-ceiling-for-persistent-parents.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 7727c0c
short: 7727c0c
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/195
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Bound final Codex header metadata

## Purpose

Resolve the focused PR 195 re-review finding that context-only byte validation
did not account for caller-controlled model metadata appended in the initial
Codex evidence header after preflight reached ready.

## Approach

Limit native hook model metadata to 512 UTF-8 bytes while constructing hook
correlation, before any turn reservation or adapter preflight. Reject oversized
or invalid UTF-8 values instead of truncating them, so the final header cannot
silently misstate host model evidence and the substantive UserPromptSubmit
fails before a ready route can be committed.

Add the reviewer's 9,000-emoji model case as a direct regression. It proves the
adapter was not called and no reservation was created. Add a curated decision
mutation that restores the unbounded read and must be killed by that test.

## Challenges encountered

The earlier 48,000-byte check correctly bounded the context-only JSON envelope,
but Codex constructs its Store-backed header only after the route is ready. The
right repair boundary is therefore the untrusted model field before preflight,
not a post-ready fallback that would discard the header or leave ready evidence
behind after rejecting final output.

## Decisions and alternatives

Use the established 512-byte native model-metadata bound. Do not raise the
65,536-byte hook cap, reduce the approved 32,000-character team context, or
truncate model identity. Keep the 17,536-byte header reserve and fail loudly at
the earliest attributable input boundary.

## Verification

- The direct 9,000-emoji regression passes and proves zero adapter calls and
  zero reservations.
- The new isolated decision mutation is killed with a green baseline, zero
  invalid results, and unchanged source.
- The affected hook, preflight, header, and security boundary passes 238 tests
  with one intentional skip.
- Ruff check and format pass the three changed Python files.
- Documentation metadata and validation pass 578 Markdown files; diff
  integrity is clean.

## Follow-ups

Rerun the named fast gate and all 53 decision mutations, update exact evidence,
push the repaired head, and complete the allowed focused P1 re-review before
merge or installation.
