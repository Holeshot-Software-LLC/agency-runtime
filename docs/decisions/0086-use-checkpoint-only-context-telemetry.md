---
title: "Use checkpoint-only context telemetry"
status: accepted
category: decisions
created: 2026-07-23
updated: 2026-07-23
tags: [governance, context, codex, reliability]
related:
  - AGENTS.md
  - scripts/context_handoff_status.py
  - scripts/verify_docs.py
  - tests/test_context_handoff_status.py
  - tests/test_verify_docs_schema.py
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/README.md
  - docs/roadmap/handoffs/issue-AR-119.md
supersedes:
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
superseded_by: null
id: ADR-0086
type: decision
deciders: [maintainers]
---

# ADR-0086: Use checkpoint-only context telemetry

## Context

The 65-percent live-evaluation admission rule was layered on top of cumulative
Codex telemetry. Normal compaction does not promise to reset that cumulative
value, so a healthy goal could establish a clean recovery checkpoint and still
be prohibited from running its next bounded live package indefinitely. The
percentage did not measure evidence quality, provider safety, capture
durability, or the task's actual ability to complete the package.

The separate 50-percent clean-checkpoint boundary remains useful. It ensures
that accumulated work and the next bounded package are durable before context
becomes tight, without manufacturing a new task or transferring task-local goal
state.

## Decision

Remove the live-evaluation admission threshold from repository policy, active
capsules, telemetry output, validation, and tests. Context telemetry has one
governed meaning: at or below 50 percent, ensure a clean substantive and ledger
checkpoint before continuing. Once that checkpoint exists, continue in the
same task, including live evaluation.

Run telemetry after bootstrap, immediately before each live evaluation, and at
bounded-package closeout. Those checks are observational for live work; they
never admit, block, pause, or defer an evaluation. A conditional rerun or
complete corpus receives its own immediately preceding check so any uncommitted
substantive work is checkpointed first.

When cumulative telemetry remains at or below 50 percent, reuse an already
clean recovery checkpoint if no substantive delta exists. Never create empty
commit pairs, wait for a percentage reset, create another task, or stop a
persistent goal solely because of the reading.

## Consequences

Long-running goals can make forward progress through normal Codex compaction
while retaining the clean checkpoint behavior. The helper and capsule schema
become smaller and cannot report a false live-work blocker. Live-evaluation
safety still comes from the package's explicit provider confirmation, fixed
budgets, durable raw capture, governed evaluation controls, and evidence-backed
closeout rather than a context percentage.

Historical worklogs and earlier roadmap evidence continue to describe the
superseded 65-percent rule faithfully. Active contracts identify it as removed.

## Alternatives

Keeping the admission threshold was rejected because cumulative telemetry can
remain below it permanently. Waiting for compaction or a new task was rejected
because neither guarantees a reset and task-local goals do not transfer.
Lowering the admission percentage was rejected because it preserves the same
unrelated blocker at a different value. Removing telemetry entirely was
rejected because the 50-percent clean checkpoint remains a useful durable
recovery control.
