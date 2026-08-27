---
title: "Bound the Codex activation child wait above observed latency"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, reliability, containers]
related:
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-318-bound-codex-activation-child-wait.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - tests/test_codex_activation_canary.py
  - tests/test_canary_coverage_complete.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0182
type: decision
deciders: [maintainers]
---

# ADR-0182: Bound the Codex activation child wait above observed latency

## Context

The AR-297 exact Codex child completed successfully but its final message
arrived at the boundary of the parent's one 60-second `wait_agent` call. Codex
returned `timed_out=true` 224 ms later, and Agency correctly refused to infer
terminal collaboration from the child Store row alone. Repeating the same
brittle timing would not provide strict production assurance.

## Decision

The exact activation canary uses one 120,000-ms native `wait_agent` call inside
the existing 600-second outer ceiling. One shared constant binds the developer
instruction and persisted-rollout validator. The protocol still permits exactly
one spawn and one wait, with no follow-up, retry, other tool, or synthetic
completion; a timeout remains a truthful failure.

## Consequences

An observed successful child has sufficient bounded time to become terminal at
the parent boundary without opening an unbounded loop. Fresh artifacts and a
fresh clean container are required because the wait is part of the candidate's
validated host protocol. All delivery, consumption, header, Store, and
attestation checks remain unchanged.

## Alternatives

Retrying identical 60-second canaries was rejected as timing-dependent evidence.
Admitting child completion directly from its rollout was rejected because the
parent's terminal collaboration result is required. Multiple waits or a
follow-up were rejected because they change the one-turn activation protocol.
An unbounded wait was rejected because it would weaken subprocess ownership and
terminal failure guarantees.
