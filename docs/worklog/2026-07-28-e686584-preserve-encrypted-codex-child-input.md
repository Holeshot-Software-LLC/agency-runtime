---
title: "Worklog detail: Preserve encrypted Codex child activation input"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [codex, hooks, activation, encryption, canary]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
supersedes: []
superseded_by: null
type: worklog
commit: e6865843f74ea5871639ccd63ad5e0fa77b1585c
short: e686584
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Preserve encrypted Codex child activation input

## Purpose

Repair the installed Codex activation failure that appeared after the first
AR-199 merge: the exact specialist prompt reached the child, but replacing the
opaque collaboration message left a mixed plaintext/encrypted envelope that
Codex could not decrypt.

## Approach

`PreToolUse` still validates the package-owned canary assignment and stages its
one-use native-hook grant, but leaves Codex's opaque message unchanged. After
the exact native child lifecycle is persisted, `SubagentStart` retrieves one
unambiguous pending grant, verifies it against the current plan, and injects
the immutable prompt as additional context without exposing the bearer token.
`PostToolUse` consumes that grant through its exact tool-call identity and the
persisted child lifecycle.

The rollout projector now reads activation context from both `message` and the
observed `agent_message` response item. It also requires one successful child
completion with a final message, so the real decrypt-error shape cannot become
a false pass.

## Challenges encountered

Codex intentionally exposes only ciphertext at the parent tool hook while the
child-start event omits the parent task label. The repair therefore uses the
existing ready plan, staged native-hook grant, and exact lifecycle identity;
ambiguous pending grants fail closed. The first focused test run also exposed
two stale test assumptions about the current hashed task-name projection.

## Decisions and alternatives

Persisting the bearer token or weakening exact goal checks was rejected.
Rewriting the encrypted tool input was also rejected because the live child
rollout proved that it creates an undecodable mixed envelope. The delivery
shift remains restricted to the closed-world Codex activation canary.

## Verification

- 66 Codex hook, activation Store, and activation-canary tests passed.
- Ruff check and format verification passed for changed production and test
  files.
- Python compilation, documentation validation, and whitespace checks passed.

## Follow-ups

Run the named fast spine, merge and exact-install the follow-up, then rerun the
trusted Codex activation verifier and capture a fresh visible header under
[AR-199](../roadmap/issue-AR-199-restore-codex-workforce-evidence.md).
