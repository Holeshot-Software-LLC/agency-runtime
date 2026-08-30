---
title: "Worklog: Bound autonomous context handoffs"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [governance, handoff, context, codex, reliability]
related:
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
supersedes: []
superseded_by: null
type: worklog
commit: 355c05a77f9656f62069e5a18ddb128f788b9461
short: 355c05a
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog: Bound autonomous context handoffs

## Purpose

Prevent ambiguous task creation from producing concurrent branch writers and
prevent unbounded historical bootstrap reads from recursively exhausting every
fresh receiver before useful work begins.

## Approach

The repository now keeps one validated active recovery capsule per long-running
issue. The capsule is capped at 12 KiB and 180 lines, uses a stable
package-specific handoff token, and carries the current checkpoint, blocker,
next package, verification, and constraints. The first capsule projects the
current AR-119 state without replacing its complete historical contract.

Repository instructions now require create-once dispatch, reconciliation after
ambiguous creation errors, bounded receiver bootstrap, prompt source-task
finalization after ownership acknowledgment, and reuse of an existing clean
checkpoint when preflight made no substantive change.

## Challenges encountered

Two task-creation calls had reported a missing handler despite creating
receivers, and a fallback created a third. After the duplicates were paused,
the retained receiver's complete AR-119 reread reduced remaining context from
84.1 percent to 26.0 percent. It briefly wrote a telemetry paragraph, removed
it on instruction, and stopped with no net changes.

The first full Python matrix ran under the restricted sandbox against a dirty
pre-commit checkout. It reached 7,159 passing tests with 205 failures and 34
skips, dominated by clean-checkout contracts, deep temporary-path failures, and
restricted process spawning. A clean-commit rerun under a short system
temporary root remained invalid because security tests correctly rejected that
cross-account-replaceable namespace. These runs are recorded as environment
blockers, not as passing product evidence and not as protocol regressions.

## Decisions and alternatives

Canonical roadmap and worklog history remains intact. Only current recovery
state is projected into the replace-in-place capsule. Immediate task-creation
retry, complete historical rereads, telemetry-only commits, and recursive
preflight delegation are prohibited.

Tracker creation was not inferred from permission to make local repairs.
AR-126 remains in progress until its same-repository tracker item is authorized
and a later real handoff proves the bounded bootstrap with exactly one receiver.

## Verification

- Focused documentation and telemetry tests passed: 28 tests.
- Ruff check passed and 536 Python files satisfy the formatter.
- Metadata validation covered 308 Markdown documents; documentation validation
  passed for all 308.
- Policy availability and worklog pre-commit checks passed.
- The AR-119 capsule is 5,354 bytes and 101 lines.
- Dashboard UI tests passed 97/97 outside the spawn-restricted sandbox.
- The routing evaluation passed every routing, policy, delegation, and
  performance gate.
- Git whitespace validation passed.

## Follow-ups

Create and map the AR-126 tracker issue only after explicit authorization. On
the next requested AR-119 continuation, use the stable capsule token and
create-once reconciliation, then record whether one receiver retains more than
half its context after bounded bootstrap.
