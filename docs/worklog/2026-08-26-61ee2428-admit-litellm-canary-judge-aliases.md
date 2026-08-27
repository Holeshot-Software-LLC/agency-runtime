---
title: "Worklog detail: Admit LiteLLM canary judge aliases"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [litellm, canary, inference, aliases]
related:
  - README.md
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-316-size-ollama-selector-judge-context.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
supersedes: []
superseded_by: null
type: worklog
commit: 61ee2428e42b8e517cecbfa5d8a7e416c1a283e8
short: 61ee2428
date: 2026-08-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-316-size-ollama-selector-judge-context.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
---

# Worklog detail: Admit LiteLLM canary judge aliases

## Purpose

Make the operator-selected LiteLLM-only AR-297 topology possible without
weakening the exact per-harness child-judge pin or changing the direct Ollama
transport after the operator declined that route.

## Approach

Admit a named `litellm` inference profile only when it declares a credential,
uses HTTPS or literal-loopback HTTP, resolves exactly once, and is narrowed to
the canary's sole Agency provider. Record AR-317 and ADR-0181, update operator
documentation, and leave the direct Ollama `num_ctx=8192` implementation
unchanged. The host rollout will preserve the shared `task-agency-router`
fallback policy while using a separate no-fallback child alias for exact proof.

## Challenges encountered

The first focused invocation exited 4 before collection because the security
harness requires an explicit OS- or owner-protected interpreter capability.
Rerunning with the existing root-owned `/usr/bin/python3.12` authority preserved
the guard and passed. The LiteLLM gateway stores model deployments and fallback
policy in PostgreSQL rather than the visible YAML, so a secret-free authenticated
snapshot was required before mutation.

## Decisions and alternatives

ADR-0181 records the routing decision. Reusing the shared router alias for the
exact child proof would leave an unbounded model-identity fallback; silently
deleting that foreign shared policy would exceed the authorized scope.

## Verification

- `AGENCY_CI_PYTHON=/usr/bin/python3.12 .venv/bin/python -m pytest` over the
  child-judge, inference-profile, provider-network, and canary coverage suites:
  158 passed, exit 0, warning-strict.
- Ruff check and format check over the changed Python paths: exit 0.
- Metadata, policy-availability, worklog, documentation, and diff checks: exit
  0; documentation validation covered 874 Markdown files.
- Context telemetry: 38.8 percent remaining, so this recovery pair precedes
  the first live alias probe.

## Follow-ups

AR-317 must create and prove the stage aliases, publish a new exact mode-0600
config, rebuild artifacts, and complete the fresh Codex transaction before the
remaining AR-297 harness packages proceed.
