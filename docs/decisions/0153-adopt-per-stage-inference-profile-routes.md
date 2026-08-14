---
title: "Adopt per-stage inference profile routes"
status: accepted
category: decisions
created: 2026-08-04
updated: 2026-08-12
tags: [routing, inference, workforce, configuration, security]
related:
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/roadmap/handoffs/issue-AR-235.md
  - agency_runtime/core/inference_profiles.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/config_defaults.yaml
  - agency_runtime/core/configuration_schema.py
supersedes: []
superseded_by: null
id: ADR-0153
type: decision
deciders: [maintainers]
---

# ADR-0153: Adopt per-stage inference profile routes

## Context

AR-235 §3 (autonomous gap hiring with isolated security review) needs to
retarget a stage end-to-end with a single configuration change, route the
security reviewer to a different model than the creator, and forward
`(model, thinking_level)` to the adapter as a provider-native parameter.
The current shape (`config_defaults.yaml:60-79`) is a flat list of four
per-stage model names with no thinking-level, no profile abstraction, no
capability class, and no independence metadata. Each new requirement
(security reviewer isolation, same-provider warning, repair-loop thinking
downgrade) is fighting the flat schema.

The conveyor project (sibling repo) already documents the
`(adapter, model, thinkingLevel, capabilityClass)` profile pattern with
routes and a default-profile fallback
(`conveyor/src/config/types.ts:294-310`,
`conveyor.config.example.json:184-238`). Agency Runtime adopts the same
shape, owning the resolver and schema so the runtime keeps its own
evidence-bound config validation pipeline.

ADR-0118 (require inference-owned specialist staffing) is the parent
decision this ADR extends. The new schema keeps inference ownership of
staffing intact; it only adds the per-stage addressability that
AR-235's security-review isolation and same-provider warning require.

## Decision

Agency Runtime adopts a per-stage inference profile schema. Each profile
declares `(adapter, model, thinking_level, capability_class, base_url,
api_key_env, api_key, timeout_ms)`. Routes map a route key
(e.g. `workforce.planner`, `workforce.hiring.security_review`) to a
named profile. A `default_profile` is used when a route key is missing.
`strict_independence` enforces a different provider for routes whose
key contains `critic` or `security_review`.

The four legacy flat `workforce.*_model` knobs are removed in this
slice. The runtime is not yet installed in production, so no
migration window is required. Routes are the only ownership path for
per-stage model selection. The reference doc
(`docs/roadmap/reference-workforce-inference-stages.md`) owns the
per-stage inventory, profile schema, and per-adapter `thinking_level`
mapping; the runtime owns the resolver and the validation pipeline.

Key consequences:

- One profile is one runnable provider. The structured provider
  translates the configured `thinking_level` into a provider-native
  parameter (`reasoning_effort` for `openai-compatible`,
  `thinking.budget_tokens` for `anthropic`, native `thinking` for
  `litellm`) and records the consumed value in the receipt alongside
  the configured value. Adapters that do not support thinking
  (`ollama`, `cli`) record the value and ignore it; the receipt still
  shows what the operator asked for.
- The security reviewer must use a different `model` and different
  `thinking_level` from the creator. Same `adapter` is allowed; same
  provider is allowed. When the same provider is used, the case ledger
  records `same_provider_as_creator: true` and the dashboard surfaces
  a warning. `strict_independence: true` makes that mismatch a
  config-load error.
- The route resolver (`agency_runtime/core/inference_profiles.py`)
  is the single resolution point. Call sites that previously
  consulted the flat knob chain (workforce `hiring`, `critic`,
  `planner`, `recruiter`) now pass an explicit `route_key` to
  `configured_workforce_providers`. When the route is missing and no
  `default_profile` is configured, the resolver falls through to the
  configured provider chain so dashboards and CLI evals that pre-date
  the inference block still work.
- The four legacy flat knobs (`workforce.planner_model`,
  `recruiter_model`, `hiring_model`, `critic_model`) are removed from
  `WorkforceConfig`, the schema validator, the YAML serializer, and
  the configuration patch surface. The migration is rip-and-replace
  because the runtime is not yet installed in production. Persisted
  documents that carry these keys fail schema validation with a
  `workforce: contains unsupported fields` error that points the
  operator at the new `inference.routes` block.

## Consequences

- Per-stage model selection is one indirection away from the operator.
  Adding a new stage is a route + profile; retargeting a stage is one
  profile edit. The deprecation surface that the slice prompt's
  `Alternatives` section described (one-time deprecation warning per
  session) is gone because the migration is immediate.
- Receipts record `thinking_level_configured` and
  `thinking_level_consumed` for every inference call. The case ledger
  and dashboard can chart thinking-level distribution per stage
  without grepping the system prompt.
- Same-provider detection is centralized in
  `shares_provider_with()` and `enforce_strict_independence()`. The
  case ledger and the dashboard surface the same fact from the same
  helper, so they cannot drift.
- The slice prompt's documented `Alternatives` (keep the flat knobs
  as a fallback with deprecation warning) is recorded here as
  **rejected** for this slice. The user explicitly chose rip-and-replace
  during greenlight because the project is not yet installed. The
  rejected alternative remains the documented escape hatch for a
  later slice if a real installed base ever needs it.
- `WorkforceConfig` shrinks by four fields. The configuration schema
  test suite (`tests/test_configuration.py`) and the dashboard UI
  test (`tests/dashboard_ui.test.mjs`) drop references to those
  fields. The dashboard "Settings" view will surface the new
  `inference.routes` and `inference.profiles` block in a follow-up
  slice (slice 6).
- Per-call cost and latency are unchanged. The structured provider
  makes one HTTP request per call; the new schema adds an
  `inference_profiles.py` lookup that runs synchronously and is
  in-process.

## Alternatives

- **Keep the flat `workforce.*_model` knobs as a fallback with
  one-time deprecation warning per session.** Rejected during
  greenlight. The runtime is not yet installed in production; the
  four knobs are removed outright. The migration cost is bounded
  to the test suite and the schema validator; persisted documents
  that reference the old keys are rejected with a clear error.
- **Extend `configured_workforce_providers` in
  `agency_runtime/core/workforce/inference.py` to own the resolver
  logic.** Rejected for separation of concerns. The resolver is
  a small, addressable surface with a single contract
  (`resolve(config, route_key) -> ProfileResolution`); colocating
  it with the workforce provider helper would couple the schema to
  the legacy `stage=` string vocabulary and make future slices
  (the security-review stage) reach into the workforce module for
  what is really a configuration concern.
- **Default profile warning: warn once per session when the resolver
  falls back to `default_profile`.** Rejected as premature. The
  default profile is the documented fallback contract; warning
  every time a route key is missing would create noise. A future
  slice can add the warning if operators report confusion about
  which stage fired which model.
- **Adopt the conveyor schema verbatim (camelCase keys, JSON
  instead of YAML).** Rejected. Agency Runtime's configuration is
  YAML and snake_case to match the existing `workforce.*` and
  `adapters.*` blocks. The shape (routes, profiles, default profile,
  strict-independence flag) is the conveyor pattern; the syntax is
  Agency's.
