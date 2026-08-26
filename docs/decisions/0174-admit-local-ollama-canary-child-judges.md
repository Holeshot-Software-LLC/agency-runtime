---
title: "Admit local Ollama canary child judges"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [canary, inference, ollama, providers, security, evidence]
related:
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
  - docs/roadmap/issue-AR-316-size-ollama-selector-judge-context.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - agency_runtime/core/canary_judge_provider.py
  - tests/test_canary_child_judge_provider.py
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0174
type: decision
deciders: [maintainers]
---

# ADR-0174: Admit local Ollama canary child judges

## Context

ADR-0160 pins each live canary's child judge to one exact provider identity and
removes fallback. It initially admitted authenticated Codex and Claude CLI
providers plus an Anthropic-compatible inference profile. AR-297's Linux
production topology instead requires a free local child judge and already has
a loopback Ollama service and an explicit named inference profile.

Rejecting that profile would force a subscription route or a new proxy solely
to change protocol shape. Automatically consulting the global Ollama fallback
would weaken the requested/answered identity proof and could change ordinary
staffing behavior.

## Decision

Permit one named `ollama` inference profile as a canary child-judge pin. Apply
the same exact single-name resolution and no-fallback projection used by every
other child pin. Require the configured endpoint to satisfy Agency's existing
safe-credential URL rule and require the materialized provider to be available
before the canary starts.

The profile is projected only into the canary's one-provider tuple. It is not
inserted into `config.providers`, does not reorder ordinary inference, and does
not create a CLI credential home. The existing structured Ollama transport
retains bounded request/response handling, no redirects, exact actual-model
receipts, and schema-only final output. A profile with no thinking level sends
`think: false`; model reasoning is not inferred from configuration prose.

Literal loopback HTTP is acceptable because the local Ollama profile carries
no credential. Non-loopback plaintext HTTP remains unsafe and is rejected
before transport. HTTPS retains the existing safe-URL treatment; this decision
does not add remote discovery, implicit models, or secret persistence.

## Consequences

- Clean offline containers can prove an exact free local child judge without
  subscription authentication or a task-specific LiteLLM service.
- Requested profile identity, response-body actual model, and native host
  delivery evidence remain separate claims.
- The canary gains no provider fallback and ordinary workforce routing remains
  unchanged.
- Live model availability and exact-model evidence remain AR-297 gates; source
  acceptance alone proves neither.

## Alternatives

- **Keep subscription-only canaries.** Rejected because it violates the
  owner-approved free local judge topology.
- **Use the global Ollama fallback implicitly.** Rejected because it loses the
  exact pin and can change ordinary routing.
- **Mutate the existing LiteLLM service.** Rejected because it would overwrite
  foreign service policy solely to adapt protocol shape.
- **Permit every HTTP inference adapter.** Rejected because the bounded change
  needs only the already-supported Ollama structured transport; broadening the
  allowlist would add unaudited credential and protocol boundaries.
