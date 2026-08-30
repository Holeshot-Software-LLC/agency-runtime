---
title: "Project config-declared credentials into tool-reduced canaries"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [canary, credentials, configuration, process, security]
related:
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/configuration_contracts.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0178
type: decision
deciders: [maintainers]
---

# ADR-0178: Project config-declared credentials into tool-reduced canaries

## Context

Agency's hardened CLI launcher intentionally keeps only platform, proxy,
certificate, and native authentication-home variables. That contract prevents
unrelated account and cloud credentials from crossing into a model-facing
process. A managed Codex activation canary, however, executes Agency hooks in
the same process tree. Those hooks load the exact Store-bound configuration and
may require a credential named by an inference profile. Removing that named
value makes an otherwise valid exact configuration unrunnable.

AR-297 reproduced this boundary with a local LiteLLM embedding route. The
installer process had the credential, the minimal Codex environment did not,
and the hook failed additive recall. The value cannot be copied into durable
configuration or managed policy, and globally allowlisting its conventional
name would expose it to unrelated CLI routing judgments.

## Decision

An Agency live canary prepared from an exact validated configuration derives a
bounded names-only set from that configuration's judge, provider, inference
profile, and adapter credential references. The safe backend first constructs
the ordinary minimal CLI environment, then projects only matching nonempty
values from the invoking process. The ordinary `safe_cli_environment` allowlist
does not change.

The projection accepts at most 256 unique, credential-shaped ASCII identifier
names and at most 64 KiB of UTF-8 text per value. A name cannot collide with the
already-built native/control environment or use the `AGENCY_CANARY_` control
prefix. Invalid, duplicate, NUL-bearing, oversized, or non-text input fails
before native process creation. Missing values are not invented. Direct
configuration keys are not copied into the environment.

Credential projection is limited to canary invocations whose native tool
surface is already reduced: Codex disables shell, unified execution, web,
apps, and MCP and retains only collaboration; Claude retains only its native
Agent boundary. Values remain process-local and never enter argv, installed
policy, service definitions, reports, logs, Store evidence, or host artifacts.
Ordinary later harness processes must receive the same credential through their
container or service-manager environment; a successful canary does not make a
secret durable.

## Consequences

Exact local or remote inference routes can execute during managed activation
without weakening the global child-environment policy. Custom credential names
work without a conventional-name exception, and inference-profile references
are covered alongside legacy providers and adapters.

The native canary process temporarily carries each selected value. Its
tool-reduced invocation and exact noninteractive prompt remain part of the
security boundary. Adding a new native tool surface requires a separate review;
this decision does not authorize credential projection into arbitrary product
trials, normal CLI judgments, or general subprocesses.

## Alternatives

Globally allowlisting `LITELLM_API_KEY` was rejected because unrelated CLI
judgments would inherit it. Persisting a key in configuration, Codex managed
policy, a service unit, or an evidence file was rejected because the existing
indirection is intentionally write-only and process-local. Disabling LiteLLM
authentication or changing to a keyless endpoint was rejected because it would
change the approved exact topology. Treating the failed embedding as optional
was rejected because additive dense recall and strict assurance are explicit
acceptance requirements.
