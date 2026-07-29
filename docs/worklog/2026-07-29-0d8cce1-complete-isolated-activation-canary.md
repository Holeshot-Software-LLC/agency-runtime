---
title: "Worklog detail: Complete isolated Codex activation canary"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [codex, canary, hooks, delegation, evidence]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0d8cce1
short: 0d8cce1
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Complete isolated Codex activation canary

## Purpose

Restore the deterministic one-specialist contract in isolated Codex Agency
canaries and complete the native activation receipt when Codex emits its spawn
result as a mapping rather than a JSON string.

## Approach

The isolated backend marks its already-existing evidence Store only for exact
Agency activation rollouts. That enters the same nonce-bound, closed-world
`code-reviewer` route used by current-profile verification and keeps semantic
planning and dynamic hiring outside the diagnostic.

The PostToolUse boundary now accepts either response representation after both
have been parsed into the same bounded mapping. The rooted native task label,
exact normalized task name, exact projected keys, persisted child lifecycle,
and one-use activation checks remain mandatory.

## Challenges encountered

The first source-level live canary proved the routing fix, one spawn, one wait,
and a completed child, but the activation grant remained unconsumed. Store
evidence isolated the failure to a redundant source-type guard after successful
response parsing. The activation contract test also still expected the removed
opaque-input rewrite instead of the current SubagentStart delivery boundary.

## Decisions and alternatives

No trust or goal-equality boundary was relaxed. The implementation reuses the
existing-store marker because the isolated activation canary already writes its
evidence into that exact pre-existing Store. It does not enable deterministic
routing for ordinary text or enable dynamic hiring inside the canary.

## Verification

- Four exact regression tests passed.
- The adjacent activation and receipt suite passed 68 tests with 2 skips.
- The named fast Python production spine passed 651 tests with 6 skips.
- Ruff check and format passed all 601 Python files.
- Dashboard UI verification passed all 109 tests.
- Metadata, policy, worklog, documentation, and diff checks passed.
- The governed external routing evaluation was not rerun because the egress
  approval gate rejected provider transmission; the immediately preceding
  exact-merge evaluation was green.

## Follow-ups

Merge and exact-install this commit, rerun the isolated canary to prove the
complete activation graph and attestation, then run the fresh USB-style task
needed to close AR-199.
