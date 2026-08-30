---
title: "Worklog detail: Preserve exact Codex child context framing"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, hooks, activation, canary, evidence]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
supersedes: []
superseded_by: null
type: worklog
commit: ea73dd506f766e57ed3e4bb4d7b7c6e6db240272
short: ea73dd5
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Preserve exact Codex child context framing

## Purpose

Make the successful exact-installed Codex child activation parseable by the
strict rollout verifier. The child already executed and returned a final
message, but surrounding `SubagentStart` prose changed the signed task and
prompt boundaries.

## Approach

An exact correlated activation now occupies the complete child-start
`additionalContext`. Its canonical task remains the bytes before the delivery
section and its immutable specialist prompt remains the terminal bytes after
the marker. Generic identity, parent-scope, and fallback guidance remains
available only to unplanned children without an exact activation.

The regression test exercises the opaque Codex call, retrieves the staged
grant at child start, reparses the complete returned context, verifies the
canonical canary goal and `code-reviewer` identity, and proves the prompt body
is the terminal context.

## Challenges encountered

The first live follow-up fixed Codex decryption and produced a successful child
result, which moved the failure into evidence projection. The parser correctly
rejected the context because prefix prose became part of `original_task` and
suffix prose became part of `prompt_body`; relaxing either hash check would
have weakened the activation contract.

## Decisions and alternatives

The strict parser and immutable hashes remain unchanged. Redundant child
identity prose was removed from exact activations because authoritative
lifecycle identity is already persisted separately. Untyped children retain
the existing safe fallback context.

## Verification

- 67 focused Codex hook, activation Store, and canary tests passed.
- Ruff check and format verification passed for changed source and tests.
- Documentation, metadata, worklog-currentness, and whitespace checks passed.

## Follow-ups

Run the proportional fast spine, merge and exact-install the follow-up, then
rerun the trusted live activation verifier under
[AR-199](../roadmap/issue-AR-199-restore-codex-workforce-evidence.md).
