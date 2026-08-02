---
title: "Authorize exact product delegation at the Codex developer boundary"
status: superseded
category: decisions
created: 2026-07-31
updated: 2026-08-01
tags: [codex, product, delegation, authority, security, evaluation]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
id: ADR-0126
type: decision
deciders: [maintainers]
---

# ADR-0126: Authorize exact product delegation at the Codex developer boundary

## Context

An exact-installed product trial reached an accepted eight-unit inferred plan,
but the Codex parent launched no native child and returned no response. The
same build's activation canary launched its selected child successfully.

The difference was authority, not selection or hook activation. The activation
canary supplies a high-priority Codex developer instruction that explicitly
authorizes its one bounded `spawn_agent` and `wait_agent` lifecycle. The product
backend supplied only lower-priority hook context. Current Codex host policy
does not permit proactive delegation from that context alone, so every accepted
product row remained `suggested` and the Stop hook correctly failed the turn.

Invoking an Agency product evaluation is explicit operator authorization to
exercise the accepted Agency plan. That authorization still must not become a
general permission to spawn arbitrary workers or let delegated children create
unbounded recursive teams.

## Decision

The Agency-mode Codex product backend supplies one source-controlled developer
instruction through the native `developer_instructions` configuration
boundary. Native-only product trials do not receive it. In Agency mode it has
three marker-scoped behaviors:

1. A parent containing `[AGENCY DELEGATION PLAN]` is only a scheduler. It must
   dispatch every accepted persisted row exactly once, preserve the exact
   `native_task_name` and decoded goal, respect `depends_on`, and use
   dependency-ready waves of at most three concurrent children.
2. A child containing a versioned `[AGENCY EXACT SPECIALIST ACTIVATION]`
   marker performs only its hook-injected specialist assignment. Plaintext
   task delivery uses v1; opaque Codex delivery uses ADR-0127's token-free v2
   context. The child may use permitted workspace tools for that assignment
   but may not spawn, wait for, or delegate to more workers.
3. An Agency-mode task containing neither marker receives no delegation
   authority from this instruction and follows ordinary native-host policy.

The parent may call only Codex's native `spawn_agent` and `wait_agent`
collaboration primitives, may perform no product work, and must wait through
the final spawn before consolidating child results. It cannot merge, omit,
broaden, decline, retry, or duplicate an accepted row. Native failures remain
failed product evidence; they never authorize a parent fallback.

The instruction does not select specialists, create plan rows, bypass hook
trust, or issue activation grants. Inference remains the sole staffing
authority, and installed hooks continue to validate each exact persisted row,
inject its immutable child prompt, and bind its one-use grant to the observed
native child.

## Consequences

- A Codex product parent has the high-priority authority required to execute an
  already accepted Agency plan instead of silently abstaining.
- The authority is bounded to the isolated Agency-mode product evaluation and
  exact persisted rows; native-only trials do not receive it, and it is not an
  arbitrary multi-agent enablement switch.
- Specialist children can perform their assigned product work without
  recursively creating teams.
- Dependency order and the four-slot host ceiling are explicit, while up to
  three ready specialists can run concurrently.
- Missing launches, retries, parent product tools, recursive delegation, or
  incomplete waits remain observable product-trial failures.

## Alternatives

- **Rely only on UserPromptSubmit context.** Rejected because the exact live
  trial proved that lower-priority context did not authorize the native spawn.
- **Tell the product prompt to request a fixed team.** Rejected because staffing
  must remain inference-owned and open-ended rather than test-authored.
- **Let the parent build the product when delegation is unavailable.** Rejected
  because that would make a generalist result pass while specialist execution
  remained fictional.
- **Allow children to recruit more workers.** Rejected because the accepted
  persisted plan already owns staffing and recursive expansion would escape
  its evidence and concurrency bounds.
