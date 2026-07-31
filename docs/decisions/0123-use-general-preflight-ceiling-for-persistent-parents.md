---
title: "Use the general preflight ceiling for persistent native parents"
status: accepted
category: decisions
created: 2026-07-31
updated: 2026-07-31
tags: [preflight, context, delegation, hosts, specialists]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0070-run-child-specific-agency-activation.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0123
type: decision
deciders: [maintainers]
---

# ADR-0123: Use the general preflight ceiling for persistent native parents

## Context

Persistent Codex, Claude, OpenClaw, Hermes, and ZCode parents deliver a compact
resident-steward contract, content-free specialist references, and the exact
native delegation plan through isolated context. Their legacy 8,192-character
ceiling predates inference-owned complete-team planning.

The README-shaped product request produced valid nine- and ten-unit specialist
teams. Their compact exact contexts measured 8,120 and 8,326 characters; the
configured sixteen-unit maximum measured about 9,534. The runtime therefore
rejected complete, safe inferred teams solely because the legacy parent ceiling
was smaller than the already-supported bounded plan.

The general preflight ceiling is 32,000 characters. Native hook output has an
independent 65,536-byte hard limit, so a context that fits by character count
can still overflow after UTF-8 and JSON encoding. Exact recipe validation
already rejects limits above 32,000, and the context-policy fingerprint binds
the effective host limits.

## Decision

Use the existing 32,000-character general preflight ceiling for persistent
native parent contexts. Keep persistent delivery isolated: parent history does
not receive full specialist prompt bodies, and native children still run their
own task-specific Agency activation.

Continue to fail before the ready state when the complete resident, specialist,
and delegation context exceeds 32,000 characters. Also fail before ready when
the exact context-only UserPromptSubmit envelope exceeds 48,000 encoded bytes;
this reserves 17,536 bytes under the native hook's 65,536-byte hard output
limit for the bounded evidence-header addition. Preserve host-specific direct
limits such as LiteLLM's 16,384-character ceiling.

Version context rendering as well as size policy. Version-11 recipes retain
their original full-goal rows; version 12 and later may use the shared-prefix
encoding. Fresh routes use version 13, whose fingerprint includes the encoded
output limit.

Do not truncate, silently omit, or deterministically shrink an inference-owned
team to meet a smaller legacy limit. The exact accepted plan either fits the
bounded parent context or fails loudly.

## Consequences

- Complete inferred teams up to the configured sixteen-unit maximum can reach
  persistent native parents without losing assignments or exact goals.
- The parent context is dual-bounded by characters and its exact UTF-8/JSON
  envelope before ready evidence is committed.
- Changing the effective limit changes the context-policy fingerprint, so an
  incompatible durable continuation cannot be silently reused.
- Larger valid teams may add prompt latency and tokens compared with the legacy
  ceiling; product telemetry must report that cost rather than hiding it.
- Existing stored recipes retain their recorded renderer and validation
  contract; fresh routes use the new character and encoded-byte ceilings.

## Alternatives

- **Retain 8,192 characters and truncate the team or goals.** Rejected because
  it changes an accepted inference decision and can remove required assurance
  or implementation work.
- **Cap inference at a smaller fixed team.** Rejected because task complexity,
  not a deterministic host quota, owns the ideal specialist plan within the
  configured sixteen-unit safety bound.
- **Raise the native hook ceiling too.** Rejected because the measured maximum
  fits under the dual preflight limits and does not require weakening the
  65,536-byte protocol boundary.
