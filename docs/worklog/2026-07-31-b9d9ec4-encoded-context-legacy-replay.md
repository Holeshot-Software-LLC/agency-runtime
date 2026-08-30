---
title: "Worklog detail: Bound encoded context and legacy replay"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [preflight, hooks, context, replay, compatibility, review]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0123-use-general-preflight-ceiling-for-persistent-parents.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: b9d9ec4
short: b9d9ec4
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/195
related_issues:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
---

# Worklog detail: Bound encoded context and legacy replay

## Purpose

Resolve both valid findings from PR 195's bounded Codex review without reducing
the owner-approved complete-team capacity or weakening the hook output limit.

## Approach

Keep the 32,000-character persistent-parent ceiling, but validate the exact
context-only UserPromptSubmit JSON envelope against a 48,000-byte reserve before
ready evidence commits. This leaves 17,536 bytes under the native 65,536-byte
hard output cap for the bounded first-pass header. Advance fresh context policy
and recipe fingerprints to version 13.

Pass the stored policy version into delegation rendering. Version-11 recipes
retain their original full `goal=` rows; version 12 and later may use the
shared-prefix and `goal_suffix=` representation.

## Challenges encountered

The first legacy-renderer test used a prefix shorter than the existing
128-character compression threshold, so both old and current renderers
correctly emitted full goals. The fixture was lengthened to exercise the
versioned branch. Ruff then reformatted both mutation anchors; the anchors were
updated and the mutations rerun.

A wider diagnostic run exposed four unrelated failures in old continuation and
resident-manager coverage fixtures. A detached worktree at pre-repair head
`8eeca6b` reproduced all four identically, so this commit does not expand into
those pre-existing test defects.

## Decisions and alternatives

Do not lower the 32,000-character ceiling or truncate multibyte contexts. The
complete accepted plan either fits both the character limit and encoded output
reserve, or preflight fails before ready. Do not reinterpret version-11 recipes
with current rendering; the stored policy version owns reconstruction.

## Verification

- Four direct P1/P2 regressions pass.
- The affected preflight, replay, and mutation-contract boundary passes 113
  tests with one intentional skip.
- Six exact versioned recipe, ready-commit, and legacy-replay nodes pass five
  tests with one platform skip.
- Both new decision mutations are killed; neither survives or is invalid, and
  the source tree remains unchanged.
- Ruff check and format pass the five touched Python files.
- Documentation metadata and validation pass 577 Markdown files.
- Diff integrity is clean.

## Follow-ups

Run the named fast gate and all 52 decision mutations, push the repaired PR
head, complete one focused re-review, then merge and exact-install before the
single new-build product trial.
