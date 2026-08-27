---
title: "Bound the Codex wait to the full child staffing path"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, native-child, timeout, reliability]
related:
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/decisions/0183-honor-pinned-canary-judge-timeout.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/activation_canary_contract.py
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - tests/test_codex_activation_canary.py
  - tests/test_canary_coverage_complete.py
  - docs/worklog/README.md
supersedes: [docs/decisions/0182-bound-codex-activation-child-wait.md]
superseded_by: null
id: ADR-0184
type: decision
deciders: [maintainers]
---

# ADR-0184: Bound the Codex wait to the full child staffing path

## Context

ADR-0182 increased the activation wait from 60 to 120 seconds after observing
one child finish at that boundary. AR-319 then allowed the pinned judge to use
its declared 120-second timeout. Fresh exact evidence exposes the full legal
path: native-child staffing may make one initial selection request and, after a
valid abstention, one separately funded repair request. The observed requests
finished successfully and untruncated in 62.1 and 62.9 seconds, but their
combined duration exceeded the parent's one 120-second wait.

## Decision

The exact Codex activation canary uses one 300,000-ms `wait_agent` call inside
the unchanged 600-second outer transaction. The bound covers two validated
120,000-ms inference calls plus 60 seconds for hook completion and the native
child's response. One shared constant still binds the developer instruction
and persisted-rollout validator. The protocol permits exactly one spawn and one
wait, with no follow-up, retry, other tool, or synthetic completion.

## Consequences

The parent can observe the complete worst-case child staffing transaction
without an unbounded wait. The change does not alter any model, alias, endpoint,
thinking level, fallback, repair count, or delivery criterion. A timeout stays
a truthful failure, and fresh artifacts plus a fresh clean container remain
mandatory.

## Alternatives

Keeping 120 seconds was rejected because it is structurally shorter than two
permitted 120-second calls. Removing the abstention repair was rejected because
it would change inference semantics to accommodate one harness. Switching to a
different model was rejected because both approved Mistral calls succeeded and
the defect is the parent budget. Multiple waits, retries, and an unbounded wait
were rejected because they weaken the exact one-turn protocol.
