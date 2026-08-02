---
title: "Require terminal product child before the next unit"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, product, execution, evidence]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
  - docs/decisions/0137-reconcile-codex-followup-completion-at-parent-stop.md
  - docs/decisions/0139-make-codex-execution-turns-self-contained.md
  - docs/decisions/0141-admit-writer-proof-only-through-agency-plans.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/product_host.py
  - tests/test_codex_activation_canary.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0142
type: decision
deciders: [maintainers]
---

# ADR-0142: Require terminal product child before the next unit

## Context

Exact locally built candidate `ae322ec` passed the named local gate and its
full-suite install passed the autonomous Codex activation canary. A subsequent
Agency writer sentinel was invalid because the harness prompt stated an
incorrect expected SHA-256. It cannot be counted as a product loss.

The same retained run nevertheless exposed an independent scheduling defect.
Its accepted plan contained five sequential rows. The parent dispatched four
specialist execution turns and advanced to each next row while every prior
worker still had `ended_at = null`. The fifth row remained only suggested when
the 300-second host deadline expired. The workspace-write proof was absent.

The product developer contract required exactly one `wait_agent` call after an
execution follow-up. A Codex wait can wake for a child commentary update before
that child reaches a terminal result. Treating any first wake as completion
breaks one-at-a-time scheduling and can terminate a product run with live,
unfinished children.

## Decision

1. Keep one activation wait per row, set its timeout to 60 seconds, and stop if
   it does not report that exact child completed its activation-only turn.
2. After the one execution follow-up, wait up to three times for that exact
   child, with a 120-second timeout per call. A nonterminal commentary wake may
   cause another wait. A timeout, failure, or third nonterminal wake stops the
   scheduler without launching another row.
3. Never launch a later row until the prior child execution is terminal. The
   parent remains collaboration-only and still executes no product work.
4. Admit one activation wait and one through three execution waits per product
   row. Preserve the global 64-wait ceiling, exact causal order, bounded
   arguments and outputs, complete child-rollout proof, and content-free
   projection. Timed-out waits remain product failures.
5. Do not change inference, specialist selection, the accepted unit graph, or
   the two-turn activation/execution protocol in this repair.

## Consequences

- Child commentary remains visible without being promoted to completion.
- A slow child can add bounded latency, but a later specialist cannot observe
  or act on a falsely completed dependency.
- Persisted rollout evidence may contain more than two waits per row while the
  activation canary retains its exact two-wait contract.
- The invalid writer sentinel remains retained and is not retried on the same
  build. A corrected sentinel requires a new immutable build after the named
  local gate passes again.

## Alternatives

- **Suppress every child commentary message.** Rejected because host and
  inherited developer policies may require progress updates; completion must
  not depend on their absence.
- **Treat the first non-timeout wake as terminal.** Rejected because the live
  run proves that a commentary wake can precede child completion.
- **Wait without a per-row ceiling.** Rejected because one stalled specialist
  could consume the entire product run without a diagnosable bound.
- **Let the parent or next child finish the prior unit.** Rejected because that
  would violate exact worker ownership and hide the failed execution boundary.
