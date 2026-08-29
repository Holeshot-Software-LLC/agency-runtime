---
title: "Route content-invalid completions to a content-fallback profile"
status: accepted
category: decisions
created: 2026-08-29
updated: 2026-08-29
tags: [reliability, workforce, inference, litellm, fallback]
related:
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/decisions/0185-enforce-child-judge-schema-at-litellm-alias.md
  - docs/roadmap/issue-AR-335-make-content-invalid-completions-reach-fallback.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - agency_runtime/core/inference_profiles.py
  - agency_runtime/core/workforce/inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0192
type: decision
deciders: [maintainers, owner]
---

# ADR-0192: Route content-invalid completions to a content-fallback profile

## Context

The 2026-08-29 ordinary-turn matrix failed on all four hosts: the planner
primary returned an HTTP 200 completion whose body was a structurally perfect
plan terminated by a stray `]}` (retained specimen), and the recruiter primary
twice returned contract-invalid content. The router-level order-2 fallback
fires only on transport failures, so a transport-successful bad completion
never reaches the qualified different-provider deployment, and the zero-retry
doctrine correctly ends the stage. An enforcement probe proved the strict
`response_format` json_schema the runtime already sends is silently dropped on
the subscription responses bridge (`drop_params: true`), so backend grammar
enforcement cannot currently close the gap for that primary.

## Decision

Add an optional global `inference.content_fallback_routes` mapping: one
additional named profile per route key, tried by the existing stage provider
loop only after the primary's completion is rejected for content (no valid
structured response, or a contract rejection that exhausts the funded
semantic repair). The mapping is not harness-scoped, never duplicates the
primary profile, adds no retries of any provider, and leaves router-level
transport fallbacks unchanged. The owner selected this mechanism on
2026-08-29 for the planner and recruiter routes, each backed by a
single-deployment LiteLLM alias pinned to the stage's proven
different-provider fallback.

## Consequences

A single malformed primary completion no longer kills a live turn; it costs
one additional bounded call to the configured fallback profile whose stage
receipts record both attempts truthfully. Stage latency on that path includes
the fallback model's response time, which the AR-297 latency exception
already covers for the planner. LiteLLM alias state grows two
single-deployment aliases that are part of the exact production contract and
require the same secret-safe snapshots and repeat probes as every alias.

## Alternatives

Enforcing the schema at the backend (ADR-0185's mechanism) was retained as
the preferred end state but is currently unreachable for the subscription
responses bridge, which drops `response_format`; it remains worth adopting
per-deployment wherever a backend honors it. Bounded deterministic repair of
malformed output was rejected previously and stays rejected: strict assurance
does not edit model output. Adding client retries of the same provider was
rejected as a violation of the zero-retry doctrine without changing the
failure distribution.
