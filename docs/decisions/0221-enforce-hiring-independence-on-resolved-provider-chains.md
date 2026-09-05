---
title: "Enforce hiring independence on resolved provider chains"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [hiring, inference, security, configuration]
related:
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/inference_profiles.py
  - agency_runtime/core/workforce/hiring.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0221
type: decision
deciders: [maintainers]
---

# ADR-0221: Enforce hiring independence on resolved provider chains

## Context

ADR-0153 defined an opt-in strict-independence control, but its profile-only
helper had no production caller. Merely calling it would miss harness-scoped
routes, environment overrides, legacy provider chains and content fallbacks.
Safety repair also creates a replacement using its own route, not necessarily
the original hiring provider. AR-348's public-entry-point reproduction has 20
strict-mode failures with 23 passing non-strict/distinct-provider controls.

## Decision

Apply the existing adapter-plus-exact-model identity rule to every pair of
entries in the actual resolved creator and reviewer chains. Names, thinking
levels and endpoints cannot make an otherwise equal pair independent. A shared
unused fallback still makes the configured chains overlap; do not silently
prune, replace, reorder or disable a provider to make the configuration pass.

The hiring boundary supplies those resolved chains to the existing
enforce_strict_independence helper. Strict mode checks both initial critic and
security reviewer before the first creator call and checks each reviewer again
at invocation. Safety repair checks its own creator chain before spending a
replacement call and before reviewing the replacement. An unused repair route
does not block an otherwise accepted original candidate.

Raise ConfigValidationError with a strict_independence prefix and conflicting
route names. The default remains false: same-provider hiring continues with
its existing security-review warning. No model calls, deterministic staffing,
automatic configuration changes or credential changes are added.

This implements ADR-0153's existing policy at the point where the effective
harness and provider chains are known. Its earlier config-load-error wording
was never implemented and is corrected here to a hiring-attempt config error;
the per-stage routing decision itself is not superseded.

## Consequences

- Strict deployments that previously silently allowed overlap now reject it.
  Configure disjoint creator/reviewer chains or explicitly retain non-strict
  warning-only policy. Do not make that choice on the owner's behalf.
- Invalid initial pairs spend zero model calls. Invalid repair pairs do not
  spend a replacement call. Checks are local configuration comparisons.
- This proves configured identity separation, not independent companies,
  serving-model identity behind opaque aliases, or review quality. Two distinct
  aliases may still resolve to the same backend; no stronger claim is made.
- AR-349's missing durable rejected-hire cases remain separate work. A config
  error must not create an applied case or enable a worker.

## Alternatives

- A global-profile-only call: misses real production resolution paths.
- Check only the successful primary: permits a same-model content fallback.
- Check only after review: spends calls on a known-invalid pairing.
- Require different adapters, companies or thinking levels: changes the existing
  identity contract and cannot prove backend independence from configuration.
