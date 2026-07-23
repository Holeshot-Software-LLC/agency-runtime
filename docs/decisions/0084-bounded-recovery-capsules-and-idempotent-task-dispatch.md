---
title: "Use bounded recovery capsules and idempotent task dispatch"
status: accepted
category: decisions
created: 2026-07-23
updated: 2026-07-23
tags: [governance, handoff, context, codex, reliability]
related:
  - AGENTS.md
  - scripts/verify_docs.py
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/README.md
  - docs/roadmap/handoffs/issue-AR-119.md
supersedes: []
superseded_by: null
id: ADR-0084
type: decision
deciders: [maintainers]
---

# ADR-0084: Use bounded recovery capsules and idempotent task dispatch

## Context

Append-only roadmap evidence can grow beyond a fresh task's safe bootstrap
budget. Requiring a receiver to reread that entire history can cross the
handoff threshold before useful work starts and recursively create more tasks.
Separately, asynchronous task creation can succeed even when its caller sees an
error, so retrying without reconciliation can create concurrent receivers on
one branch.

## Decision

Keep full history in the canonical roadmap and worklog system, and maintain one
validated active recovery capsule for each long-running issue that needs a
handoff. The capsule is a replace-in-place current-state projection capped at
12 KiB and 180 lines. It carries a stable package-specific handoff token,
branch, evidence commit, minimum ledger commit, tracker binding, exact blocker,
one next package, verification commands, and constraints.

Receivers bootstrap from the repository instructions, active capsule, live
tracker, and latest linked worklog. They consult only capsule-referenced parts
of the historical roadmap before editing. Task creation is attempted once per
token. Any timeout or ambiguous error is reconciled against the task list before
retry. Duplicate matches are paused before edits and reduced to one verified
receiver.

A receiver that exhausts context during read-only bootstrap stops at the
existing clean checkpoint and reports a blocker. It does not write a telemetry
note, create an empty recovery/ledger pair, or delegate again. A source with no
substantive delta likewise reuses the existing checkpoint.

## Consequences

Fresh tasks receive enough current evidence to act without replaying an
unbounded transcript. Stable tokens make ambiguous creation outcomes
reconcilable, and no-op prohibitions prevent recursive commit and task churn.
The capsule adds one maintained projection that must be updated whenever the
next package changes, while the canonical issue remains the complete source of
truth.

## Alternatives

Continuing to append every handoff to the canonical issue was rejected because
bootstrap cost grows without bound. Retrying task creation immediately after an
error was rejected because the operation may already have succeeded. Creating
a commit for every read-only preflight was rejected because it advances history
without evidence and feeds the same relay loop. Relying only on a pasted prompt
was rejected because recovery state would not be independently verifiable from
the repository.
