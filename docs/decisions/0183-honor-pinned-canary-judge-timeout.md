---
title: "Honor the pinned canary judge profile timeout"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [canary, inference, timeout, reliability]
related:
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - agency_runtime/core/canary_judge_provider.py
  - tests/test_canary_child_judge_provider.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0183
type: decision
deciders: [maintainers]
---

# ADR-0183: Honor the pinned canary judge profile timeout

## Context

AR-319's exact Codex run proves that the repaired native wait is effective, but
the single pinned child judge stops at the legacy 60-second aggregate boundary.
Its inference profile already declares a validated 120-second timeout. Provider
projection carries that bound into the `ProviderEntry`, then canary narrowing
leaves `JudgeConfig.timeout=60`, causing the total attempt budget to override
the more specific pinned-provider contract at 60,091 ms.

## Decision

A canary-only explicit provider pin uses that resolved provider's validated
timeout as both its per-attempt and aggregate judge budget. The narrowed copy
still contains exactly one provider and no fallback; the ordinary configuration
object, global judge schema, aliases, models, endpoints, and thinking settings
remain unchanged. The selector's internal transport ceiling admits the existing
120-second provider/profile maximum, while ordinary `judge.timeout` input stays
schema-capped at 60 seconds.

## Consequences

Slow local judges receive the timeout already declared by the exact profile,
while a timeout remains a truthful terminal failure. The change is canary-only
and cannot enlarge ordinary provider chains or silently select a different
route. Fresh artifacts and a fresh clean container remain mandatory evidence.

## Alternatives

Raising the global judge schema ceiling was rejected because ordinary routing
does not need a broader budget. Retrying the failed provider was rejected
because the canary pin is single-attempt and no-fallback. Changing the model or
alias was rejected because the observed defect is a conflicting timeout bound,
not an unknown route. Treating identity-only delivery as staffing proof was
rejected because it would violate the host-authored v6 evidence boundary.
